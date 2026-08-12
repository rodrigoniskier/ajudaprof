(() => {
    "use strict";

    const tabs = Array.from(document.querySelectorAll("[data-tab]"));
    const panels = Array.from(document.querySelectorAll("[data-panel]"));
    const toast = document.getElementById("toast");
    const overlay = document.getElementById("loading-overlay");
    const loadingMessage = document.getElementById("loading-message");
    const loadingElapsed = document.getElementById("loading-elapsed");
    let toastTimer = null;

    function showToast(message, isError = false) {
        if (!toast) return;
        window.clearTimeout(toastTimer);
        toast.textContent = message;
        toast.classList.toggle("is-error", isError);
        toast.hidden = false;
        toastTimer = window.setTimeout(() => {
            toast.hidden = true;
        }, isError ? 8000 : 5000);
    }

    function activateTab(name, { focus = false, updateHash = true } = {}) {
        const targetTab = tabs.find((tab) => tab.dataset.tab === name);
        const targetPanel = panels.find((panel) => panel.dataset.panel === name);
        if (!targetTab || !targetPanel) return;

        tabs.forEach((tab) => {
            const active = tab === targetTab;
            tab.classList.toggle("is-active", active);
            tab.setAttribute("aria-selected", String(active));
            tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
            const active = panel === targetPanel;
            panel.classList.toggle("is-active", active);
            panel.hidden = !active;
        });

        if (updateHash) {
            history.replaceState(null, "", `#${name}`);
        }
        if (focus) targetTab.focus();
    }

    tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activateTab(tab.dataset.tab));
        tab.addEventListener("keydown", (event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            let targetIndex = index;
            if (event.key === "ArrowLeft") targetIndex = (index - 1 + tabs.length) % tabs.length;
            if (event.key === "ArrowRight") targetIndex = (index + 1) % tabs.length;
            if (event.key === "Home") targetIndex = 0;
            if (event.key === "End") targetIndex = tabs.length - 1;
            activateTab(tabs[targetIndex].dataset.tab, { focus: true });
        });
    });

    const initialTab = window.location.hash.replace("#", "");
    if (tabs.some((tab) => tab.dataset.tab === initialTab)) {
        activateTab(initialTab, { updateHash: false });
    }

    function updateRepeater(repeater) {
        const rows = Array.from(repeater.querySelectorAll(":scope > [data-row]"));
        const minRows = Number.parseInt(repeater.dataset.minRows || "1", 10);
        rows.forEach((row, index) => {
            const number = row.querySelector(":scope > .row-index");
            const remove = row.querySelector(":scope > [data-remove-row]");
            if (number) number.textContent = String(index + 1);
            if (remove) remove.disabled = rows.length <= minRows;
        });
    }

    document.querySelectorAll("[data-repeater]").forEach((repeater) => {
        updateRepeater(repeater);
        repeater.addEventListener("click", (event) => {
            const addButton = event.target.closest("[data-add-row]");
            if (addButton) {
                const template = repeater.querySelector(":scope > template");
                if (!template) return;
                const row = template.content.firstElementChild.cloneNode(true);
                repeater.insertBefore(row, addButton);
                updateRepeater(repeater);
                const firstControl = row.querySelector("input, select, textarea");
                if (firstControl) firstControl.focus();
                return;
            }

            const removeButton = event.target.closest("[data-remove-row]");
            if (removeButton && !removeButton.disabled) {
                removeButton.closest("[data-row]").remove();
                updateRepeater(repeater);
            }
        });
    });

    function validateEvaluation(form) {
        if (form.id !== "evaluation-form") return true;
        const bloomChecked = form.querySelectorAll('input[name="av_bloom[]"]:checked').length;
        if (!bloomChecked) {
            showToast("Selecione ao menos um nível da Taxonomia de Bloom.", true);
            return false;
        }
        const difficulty = ["av_facil", "av_media", "av_dificil"].reduce((sum, name) => {
            return sum + Number.parseInt(form.elements[name].value || "0", 10);
        }, 0);
        if (difficulty !== 100) {
            showToast("Os percentuais de dificuldade devem somar 100%.", true);
            return false;
        }
        const total = Number.parseInt(form.elements.av_numero_questoes.value || "0", 10);
        const groupTotal = Array.from(form.querySelectorAll('input[name="av_quantidade[]"]')).reduce((sum, input) => {
            return sum + Number.parseInt(input.value || "0", 10);
        }, 0);
        if (total !== groupTotal) {
            showToast(`A soma das quantidades por tipo (${groupTotal}) deve ser igual ao total (${total}).`, true);
            return false;
        }
        return true;
    }

    function filenameFromDisposition(header) {
        if (!header) return "documento.docx";
        const utfMatch = header.match(/filename\*=UTF-8''([^;]+)/i);
        if (utfMatch) return decodeURIComponent(utfMatch[1]);
        const plainMatch = header.match(/filename="?([^";]+)"?/i);
        return plainMatch ? plainMatch[1] : "documento.docx";
    }

    async function parseError(response) {
        const type = response.headers.get("content-type") || "";
        if (type.includes("application/json")) {
            const payload = await response.json();
            return payload.message || "Não foi possível gerar o documento.";
        }
        return "Não foi possível gerar o documento. Recarregue a página e tente novamente.";
    }

    function setFormStatus(form, message, kind = "progress") {
        let status = form.querySelector(":scope > .generation-status");
        if (!status) {
            status = document.createElement("div");
            status.className = "generation-status";
            status.setAttribute("role", "status");
            status.setAttribute("aria-live", "polite");
            const submit = form.querySelector(':scope > [type="submit"]');
            form.insertBefore(status, submit || null);
        }
        status.textContent = message;
        status.dataset.kind = kind;
        status.hidden = !message;
        if (kind === "error") status.setAttribute("role", "alert");
        else status.setAttribute("role", "status");
    }

    document.querySelectorAll(".generator-form").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!form.reportValidity() || !validateEvaluation(form)) return;

            const submit = form.querySelector('[type="submit"]');
            const originalText = submit ? submit.innerHTML : "";
            if (submit) {
                submit.disabled = true;
                submit.innerHTML = "Gerando…";
            }
            if (overlay) overlay.hidden = false;
            setFormStatus(form, "Anexos recebidos. Preparando a geração…");

            const startedAt = Date.now();
            const isApostila = form.action.endsWith("/apostila");
            const isAvaliacao = form.action.endsWith("/avaliacao");
            if (loadingMessage) {
                if (isApostila) {
                    loadingMessage.textContent = "Analisando o plano e redigindo a apostila. O limite seguro é de aproximadamente 3 minutos.";
                } else if (isAvaliacao) {
                    loadingMessage.textContent = "Analisando os conteúdos e elaborando as questões, o gabarito e as rubricas. O limite seguro é de aproximadamente 3 minutos.";
                } else {
                    loadingMessage.textContent = "O Gemini está analisando os anexos e compondo o arquivo. Não feche esta página.";
                }
            }
            const progressTimer = window.setInterval(() => {
                const seconds = Math.floor((Date.now() - startedAt) / 1000);
                if (loadingElapsed) loadingElapsed.textContent = `Tempo decorrido: ${seconds} s`;
                if (seconds >= 30) setFormStatus(form, `Geração em andamento — ${seconds} segundos decorridos.`);
            }, 1000);

            const controller = new AbortController();
            const browserTimeout = window.setTimeout(() => controller.abort(), 210000);

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: new FormData(form),
                    headers: { "Accept": "application/json" },
                    credentials: "same-origin",
                    signal: controller.signal,
                });
                if (!response.ok) throw new Error(await parseError(response));

                const responseType = response.headers.get("content-type") || "";
                if (!responseType.includes("wordprocessingml.document") && !responseType.includes("application/zip")) {
                    throw new Error("O servidor respondeu sem um documento. Consulte o log do PythonAnywhere e tente novamente.");
                }

                const blob = await response.blob();
                const filename = filenameFromDisposition(response.headers.get("content-disposition"));
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.setTimeout(() => URL.revokeObjectURL(url), 1500);
                const generationSeconds = response.headers.get("x-generation-seconds");
                const successMessage = generationSeconds
                    ? `Documento gerado em ${generationSeconds} s. Faça a revisão antes de utilizá-lo.`
                    : "Documento gerado. Faça a revisão pedagógica e institucional antes de utilizá-lo.";
                setFormStatus(form, successMessage, "success");
                showToast(successMessage);
            } catch (error) {
                let message = error.message || "Falha de conexão. Tente novamente.";
                if (error.name === "AbortError") {
                    message = isAvaliacao
                        ? "A avaliação ultrapassou 3 minutos e foi interrompida. Reduza o número de questões e envie somente os materiais avaliados."
                        : isApostila
                            ? "A apostila ultrapassou 3 minutos e foi interrompida. Use a extensão Breve e remova referências opcionais extensas."
                            : "A geração ultrapassou 3 minutos e foi interrompida. Reduza os anexos e tente novamente.";
                }
                setFormStatus(form, message, "error");
                showToast(message, true);
            } finally {
                window.clearInterval(progressTimer);
                window.clearTimeout(browserTimeout);
                if (overlay) overlay.hidden = true;
                if (loadingElapsed) loadingElapsed.textContent = "";
                if (submit) {
                    submit.disabled = false;
                    submit.innerHTML = originalText;
                }
            }
        });
    });
})();
