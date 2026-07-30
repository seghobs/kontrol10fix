function escapeHtml(text) {
    if (!text) return "";
    const map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

function showAlert(message, type = "success") {
    const alertContainer = document.getElementById("alertContainer");
    const alert = document.createElement("div");
    alert.className = `alert alert-${type}`;

    const icon = type === "success" ? "check-circle" : type === "error" ? "exclamation-triangle" : "info-circle";
    alert.innerHTML = `<i class="fas fa-${icon}"></i><span>${escapeHtml(message)}</span>`;
    alertContainer.appendChild(alert);

    setTimeout(() => {
        alert.remove();
    }, 5000);
}

function slideDown(el) {
    if (!el) return;
    if (el._timer) clearTimeout(el._timer);
    
    el.classList.remove("collapsed");
    el.style.maxHeight = "0px";
    el.style.opacity = "0";
    void el.offsetHeight; // force reflow
    el.style.maxHeight = el.scrollHeight + "px";
    el.style.opacity = "1";
    
    el._timer = setTimeout(() => {
        el.style.maxHeight = "none";
        el.style.opacity = "";
        el._timer = null;
    }, 400);
}

function slideUp(el) {
    if (!el) return;
    if (el._timer) clearTimeout(el._timer);
    
    el.style.maxHeight = el.scrollHeight + "px";
    el.style.opacity = "1";
    void el.offsetHeight; // force reflow
    el.style.maxHeight = "0px";
    el.style.opacity = "0";
    
    el._timer = setTimeout(() => {
        el.classList.add("collapsed");
        el.style.maxHeight = "";
        el.style.opacity = "";
        el._timer = null;
    }, 400);
}

function closeAllPanels(exceptId) {
    const panels = [
        { id: "addTokenBody", headerId: "addTokenHeader", close: () => {
            const body = document.getElementById("addTokenBody");
            const header = document.getElementById("addTokenHeader");
            if (body && !body.classList.contains("collapsed")) {
                slideUp(body);
                if (header) header.classList.remove("open");
            }
        }},
        { id: "tokensListBody", headerId: "tokensListHeader", close: () => {
            const body = document.getElementById("tokensListBody");
            const header = document.getElementById("tokensListHeader");
            if (body && !body.classList.contains("collapsed")) {
                slideUp(body);
                if (header) header.classList.remove("open");
            }
        }},
        { id: "exemptionsSectionBody", headerId: "exemptionsHeader", close: () => {
            const body = document.getElementById("exemptionsSectionBody");
            const header = document.getElementById("exemptionsHeader");
            if (body && !body.classList.contains("collapsed")) {
                slideUp(body);
                if (header) header.classList.remove("open");
            }
        }},
        { id: "globalExemptionBody", headerId: "globalExemptionHeader", close: () => {
            const body = document.getElementById("globalExemptionBody");
            const chevron = document.getElementById("globalExemptionChevron");
            if (body && !body.classList.contains("collapsed")) {
                slideUp(body);
                if (chevron) chevron.classList.remove("rotated");
            }
        }},
        { id: "automationBody", headerId: "automationHeader", close: () => {
            const body = document.getElementById("automationBody");
            const chevron = document.getElementById("automationChevron");
            if (body && !body.classList.contains("collapsed")) {
                slideUp(body);
                if (chevron) chevron.classList.remove("rotated");
            }
        }},
        { id: "auditBody", headerId: "auditHeader", close: () => {
            const body = document.getElementById("auditBody");
            const header = document.getElementById("auditHeader");
            if (body && !body.classList.contains("collapsed")) {
                slideUp(body);
                if (header) header.classList.remove("open");
            }
        }},
        { id: "designSettingsBody", headerId: "designSettingsHeader", close: () => {
            const body = document.getElementById("designSettingsBody");
            const chevron = document.getElementById("designSettingsChevron");
            if (body && !body.classList.contains("collapsed")) {
                slideUp(body);
                if (chevron) chevron.style.transform = 'rotate(0deg)';
            }
        }}
    ];

    panels.forEach(panel => {
        if (panel.id !== exceptId) {
            panel.close();
        }
    });
}

function toggleAddTokenPanel() {
    const body = document.getElementById("addTokenBody");
    const header = document.getElementById("addTokenHeader");
    const isCollapsed = body.classList.contains("collapsed");

    if (isCollapsed) {
        closeAllPanels("addTokenBody");
        slideDown(body);
        header.classList.add("open");
    } else {
        slideUp(body);
        header.classList.remove("open");
    }
}

function toggleTokensListPanel() {
    const body = document.getElementById("tokensListBody");
    const header = document.getElementById("tokensListHeader");
    const isCollapsed = body.classList.contains("collapsed");

    if (isCollapsed) {
        closeAllPanels("tokensListBody");
        slideDown(body);
        header.classList.add("open");
        if (!body.dataset.loaded) {
            loadTokens();
            body.dataset.loaded = "true";
        }
    } else {
        slideUp(body);
        header.classList.remove("open");
    }
}

async function scrollToAndHighlightTokens(type) {
    const tokensListBody = document.getElementById("tokensListBody");
    const tokensListHeader = document.getElementById("tokensListHeader");
    const tokensListSection = document.getElementById("tokensListSection");
    let needsLoad = false;
    
    if (tokensListBody.classList.contains("collapsed")) {
        tokensListBody.classList.remove("collapsed");
        tokensListHeader.classList.add("open");
        needsLoad = true;
    }
    
    const needsHidden = (type === 'inactive' || type === 'deleted' || type === 'all');
    if (needsHidden && !_showHidden) {
        _showHidden = true;
        const btn = document.getElementById("showHiddenBtn");
        const textEl = document.getElementById("showHiddenText");
        const iconEl = btn.querySelector("i");
        if (btn) btn.classList.add("active");
        if (textEl) textEl.textContent = "Gizlenenleri Gizle";
        if (iconEl) iconEl.className = "fas fa-eye";
        _tokenPage = 1;
        needsLoad = true;
    } else if (!needsHidden && _showHidden) {
        _showHidden = false;
        const btn = document.getElementById("showHiddenBtn");
        const textEl = document.getElementById("showHiddenText");
        const iconEl = btn.querySelector("i");
        if (btn) btn.classList.remove("active");
        if (textEl) textEl.textContent = "Gizlenenleri G\u00f6r";
        if (iconEl) iconEl.className = "fas fa-eye-slash";
        _tokenPage = 1;
        needsLoad = true;
    }
    
    if (needsLoad || !tokensListBody.dataset.loaded) {
        await loadTokens();
        tokensListBody.dataset.loaded = "true";
    }
    
    setTimeout(() => {
        const cards = document.querySelectorAll(".token-card");
        let firstMatch = null;
        
        cards.forEach(card => {
            let matches = false;
            const isInactive = card.classList.contains('inactive');
            const isDeleted = card.innerHTML.includes('Geri Al');
            
            if (type === 'all') matches = true;
            else if (type === 'active' && !isInactive && !isDeleted) matches = true;
            else if (type === 'inactive' && isInactive && !isDeleted) matches = true;
            else if (type === 'deleted' && isDeleted) matches = true;
            
            if (matches) {
                card.classList.remove('highlight-pulse');
                void card.offsetWidth;
                card.classList.add('highlight-pulse');
                if (!firstMatch) firstMatch = card;
            }
        });
        
        if (firstMatch) {
            firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else if (tokensListSection) {
            tokensListSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 100);
}

function toggleExemptionsPanel() {
    const body = document.getElementById("exemptionsSectionBody");
    const header = document.getElementById("exemptionsHeader");
    const isCollapsed = body.classList.contains("collapsed");

    if (isCollapsed) {
        closeAllPanels("exemptionsSectionBody");
        slideDown(body);
        header.classList.add("open");
        if (!body.dataset.loaded) {
            loadExemptions();
            body.dataset.loaded = "true";
        }
    } else {
        slideUp(body);
        header.classList.remove("open");
    }
}

function toggleAuditPanel() {
    const body = document.getElementById("auditBody");
    const header = document.getElementById("auditHeader");
    if (!body || !header) return;
    const isCollapsed = body.classList.contains("collapsed");
    if (isCollapsed) {
        closeAllPanels("auditBody");
        slideDown(body);
        header.classList.add("open");
        if (!body.dataset.loaded) {
            loadAuditLogs();
            body.dataset.loaded = "true";
        }
    } else {
        slideUp(body);
        header.classList.remove("open");
    }
}

async function loadAuditLogs() {
    const loading = document.getElementById("auditLoading");
    const list = document.getElementById("auditList");
    if (!list) return;
    if (loading) loading.classList.add("show");
    list.innerHTML = "";
    try {
        const r = await fetch("/admin/get_audit_logs?limit=100");
        const d = await r.json();
        if (loading) loading.classList.remove("show");
        if (!d.success || !d.logs || d.logs.length === 0) {
            list.innerHTML = '<div class="empty-state" style="padding: 20px;"><i class="fas fa-history"></i><p>Islem kaydi yok.</p></div>';
            return;
        }
        d.logs.forEach((log) => {
            const div = document.createElement("div");
            div.style.cssText = "padding: 10px 12px; margin-bottom: 8px; background: #0d0a08; border-radius: 8px; font-size: 13px; border: 1px solid rgba(139, 109, 78, 0.15); word-break: break-all; overflow-wrap: anywhere;";
            
            const isPostLink = log.entity_id && (log.entity_id.startsWith("http://") || log.entity_id.startsWith("https://"));
            if (isPostLink) {
                div.style.cursor = "pointer";
                div.style.transition = "all 0.2s ease";
                div.onmouseover = () => {
                    div.style.borderColor = "rgba(196, 149, 106, 0.4)";
                    div.style.background = "rgba(196, 149, 106, 0.03)";
                };
                div.onmouseout = () => {
                    div.style.borderColor = "rgba(139, 109, 78, 0.15)";
                    div.style.background = "#0d0a08";
                };
                div.onclick = () => showAuditPostDetails(log.entity_id);
            }
            
            const actionLabel = { token_eklendi: "Token eklendi", token_guncellendi: "Token guncellendi", token_silindi: "Token silindi", token_geri_alindi: "Token geri alindi", relogin_basarili: "Tekrar giris" }[log.action] || log.action;
            div.innerHTML = "<strong>" + escapeHtml(log.entity_id) + "</strong> – " + escapeHtml(actionLabel) + (log.details ? " – " + escapeHtml(log.details) : "") + " <span style=\"color: rgba(255,255,255,0.5); font-size: 12px;\">" + escapeHtml(log.created_at) + "</span>";
            list.appendChild(div);
        });
    } catch (e) {
        if (loading) loading.classList.remove("show");
        list.innerHTML = '<div class="empty-state" style="padding: 20px;"><p>Yuklenemedi.</p></div>';
    }
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return response.json();
}

async function loadExemptions() {
    const loading = document.getElementById("exemptionsLoading");
    const list = document.getElementById("exemptionsList");
    loading.classList.add("show");
    list.innerHTML = "";

    const search = document.getElementById("exemptionSearch") ? document.getElementById("exemptionSearch").value.trim() : "";
    const pageSize = document.getElementById("exemptionPageSize") ? parseInt(document.getElementById("exemptionPageSize").value, 10) : 25;
    const url = new URL("/admin/get_exemptions", window.location.origin);
    if (search) url.searchParams.set("search", search);
    url.searchParams.set("page", String(_exemptionPage));
    url.searchParams.set("page_size", String(pageSize));

    try {
        const response = await fetch(url.toString());
        const data = await response.json();

        loading.classList.remove("show");
        if (!data.success) throw new Error(data.message || "Izinli liste yuklenemedi");

        _exemptionTotal = data.total || 0;
        _exemptionTotalGroups = data.total_groups || 0;
        const groups = data.groups || [];
        const totalPages = pageSize ? Math.max(1, Math.ceil(_exemptionTotalGroups / pageSize)) : 1;
        const paginationInfo = document.getElementById("exemptionPaginationInfo");
        const prevBtn = document.getElementById("exemptionPrevPage");
        const nextBtn = document.getElementById("exemptionNextPage");
        const pageSizeSelector = document.getElementById("exemptionPageSize");
        
        const showPagination = totalPages > 1;
        
        if (pageSizeSelector) {
            pageSizeSelector.style.display = _exemptionTotalGroups > 10 ? "inline-block" : "none";
        }
        
        if (paginationInfo) {
            paginationInfo.textContent = _exemptionTotalGroups + " link, " + _exemptionTotal + " kullanici, sayfa " + _exemptionPage + " / " + totalPages;
            paginationInfo.style.display = showPagination ? "inline" : "none";
        }
        if (prevBtn) {
            prevBtn.disabled = _exemptionPage <= 1;
            prevBtn.style.display = showPagination ? "inline-block" : "none";
        }
        if (nextBtn) {
            nextBtn.disabled = _exemptionPage >= totalPages;
            nextBtn.style.display = showPagination ? "inline-block" : "none";
        }

        if (groups.length === 0) {
            list.innerHTML = '<div class="empty-state" style="padding: 25px 10px;"><i class="fas fa-user-slash"></i><p>Kayit yok.</p></div>';
            return;
        }

        groups.forEach((group) => {
            const card = document.createElement("div");
            card.className = "exemption-card";

            const link = document.createElement("div");
            link.className = "exemption-link";
            link.innerHTML = `<strong>Link:</strong> ${escapeHtml(group.post_link)}`;
            card.appendChild(link);

            const users = document.createElement("div");
            users.className = "exemption-users";

            group.usernames.forEach((username) => {
                const chip = document.createElement("span");
                chip.className = "exemption-chip";

                const label = document.createElement("span");
                label.textContent = `@${username}`;

                const removeBtn = document.createElement("button");
                removeBtn.type = "button";
                removeBtn.className = "chip-remove";
                removeBtn.innerHTML = "<i class=\"fas fa-times\"></i>";
                removeBtn.title = "Kaldir";
                removeBtn.addEventListener("click", () => removeExemption(group.post_link, username));

                chip.appendChild(label);
                chip.appendChild(removeBtn);
                users.appendChild(chip);
            });

            card.appendChild(users);

            const actions = document.createElement("div");
            actions.className = "token-actions";

            const removeAllBtn = document.createElement("button");
            removeAllBtn.type = "button";
            removeAllBtn.className = "btn btn-danger";
            removeAllBtn.innerHTML = `<i class="fas fa-trash"></i> Linkteki Tum Izinlileri Sil (${group.count})`;
            removeAllBtn.addEventListener("click", () => removeExemptionsByLink(group.post_link));

            actions.appendChild(removeAllBtn);
            card.appendChild(actions);

            list.appendChild(card);
        });
    } catch (error) {
        loading.classList.remove("show");
        showAlert(`Izinli liste yuklenemedi: ${error.message}`, "error");
    }
}

async function addExemptionAdmin(postLink, username) {
    const data = await postJson("/admin/add_exemption", { post_link: postLink, username });
    if (!data.success) {
        throw new Error(data.message || "Ekleme basarisiz");
    }
    return data;
}

async function removeExemption(postLink, username) {
    if (!confirm(`@${username} izinli listesinden kaldirilsin mi?`)) {
        return;
    }

    try {
        const data = await postJson("/admin/delete_exemption", { post_link: postLink, username });
        if (!data.success) {
            showAlert(data.message || "Kaldirma basarisiz", "error");
            return;
        }
        showAlert(data.message, "success");
        loadExemptions();
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
}

async function removeExemptionsByLink(postLink) {
    if (!confirm("Bu linkteki tum izinli kullanicilar kaldirilacak. Devam edilsin mi?")) {
        return;
    }

    try {
        const data = await postJson("/admin/delete_exemptions_by_link", { post_link: postLink });
        if (!data.success) {
            showAlert(data.message || "Silme basarisiz", "error");
            return;
        }
        showAlert(data.message, "success");
        loadExemptions();
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
}

function toggleGlobalExemptionPanel() {
    const body = document.getElementById("globalExemptionBody");
    const header = document.getElementById("globalExemptionHeader");
    const chevron = document.getElementById("globalExemptionChevron");
    if (!body || !header || !chevron) return;
    
    const isCollapsed = body.classList.contains("collapsed");
    if (isCollapsed) {
        closeAllPanels("globalExemptionBody");
        slideDown(body);
        chevron.classList.add("rotated");
        loadGlobalExemptions();
    } else {
        slideUp(body);
        chevron.classList.remove("rotated");
    }
}

async function loadGlobalExemptions() {
    const loading = document.getElementById("globalExemptionsLoading");
    const list = document.getElementById("globalExemptionsList");
    const countEl = document.getElementById("globalExemptionCount");
    
    if (!loading || !list) return;
    
    loading.style.display = "flex";
    list.innerHTML = "";
    
    try {
        const r = await fetch("/admin/get_global_exemptions");
        const data = await r.json();
        
        loading.style.display = "none";
        
        if (!data.success) {
            showAlert(data.message || "Yukleme basarisiz", "error");
            return;
        }
        
        const exemptions = data.exemptions || [];
        
        if (countEl) {
            countEl.textContent = `(${exemptions.length} kullanici)`;
        }
        
        if (exemptions.length === 0) {
            list.innerHTML = '<p style="color: rgba(255,255,255,0.5);">Muaf kullanici yok</p>';
            return;
        }
        
        exemptions.forEach(ex => {
            const chip = document.createElement("div");
            chip.className = "exemption-chip";
            chip.style.background = "rgba(46, 204, 113, 0.2)";
            chip.style.border = "1px solid rgba(46, 204, 113, 0.4)";
            chip.style.padding = "6px 12px";
            chip.style.borderRadius = "20px";
            chip.style.display = "inline-flex";
            chip.style.alignItems = "center";
            chip.style.gap = "8px";
            chip.style.color = "#2ecc71";
            chip.style.fontSize = "14px";
            
            chip.innerHTML = `
                <i class="fas fa-shield-alt"></i>
                <span>@${escapeHtml(ex.username)}</span>
                <i class="fas fa-times" style="cursor: pointer; opacity: 0.7;" onclick="removeGlobalExemption('${escapeHtml(ex.username)}')"></i>
            `;
            list.appendChild(chip);
        });
    } catch (error) {
        loading.style.display = "none";
        showAlert(`Yukleme hatasi: ${error.message}`, "error");
    }
}

async function addGlobalExemption() {
    const input = document.getElementById("global_exemption_username");
    const username = input.value.trim().replace(/^@+/, "");
    
    if (!username) {
        showAlert("Kullanici adi gerekli", "error");
        return;
    }
    
    try {
        const data = await postJson("/admin/add_global_exemption", { username });
        if (!data.success) {
            showAlert(data.message || "Eklenemedi", "error");
            return;
        }
        showAlert(data.message, "success");
        input.value = "";
        loadGlobalExemptions();
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
}

async function removeGlobalExemption(username) {
    try {
        const data = await postJson("/admin/remove_global_exemption", { username });
        if (!data.success) {
            showAlert(data.message || "Silinemedi", "error");
            return;
        }
        showAlert(data.message, "success");
        loadGlobalExemptions();
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
}

let _showHidden = false;
let _tokenPage = 1;
let _tokenPageSize = 25;
let _tokenTotal = 0;
let _exemptionPage = 1;
let _exemptionPageSize = 25;
let _exemptionTotal = 0;
let _exemptionTotalGroups = 0;

async function loadStats() {
    try {
        const r = await fetch("/admin/get_stats");
        const d = await r.json();
        if (!d.success) return;
        document.getElementById("statTotal").textContent = d.total_tokens ?? 0;
        document.getElementById("statActive").textContent = d.active_tokens ?? 0;
        document.getElementById("statInactive").textContent = d.inactive_tokens ?? 0;
        document.getElementById("statDeleted").textContent = d.deleted_tokens ?? 0;
        document.getElementById("statRelogin").textContent = d.relogin_last_7_days ?? 0;
    } catch (e) {}
}

function toggleHiddenTokens() {
    _showHidden = !_showHidden;
    const btn = document.getElementById("showHiddenBtn");
    const textEl = document.getElementById("showHiddenText");
    const iconEl = btn.querySelector("i");
    if (_showHidden) {
        btn.classList.add("active");
        textEl.textContent = "Gizlenenleri Gizle";
        iconEl.className = "fas fa-eye";
    } else {
        btn.classList.remove("active");
        textEl.textContent = "Gizlenenleri G\u00f6r";
        iconEl.className = "fas fa-eye-slash";
    }
    _tokenPage = 1;
    loadTokens();
}

async function loadTokens() {
    const loading = document.getElementById("loading");
    const tokensList = document.getElementById("tokensList");
    loading.classList.add("show");
    tokensList.innerHTML = "";

    const search = document.getElementById("tokenSearch") ? document.getElementById("tokenSearch").value.trim() : "";
    const pageSize = document.getElementById("tokenPageSize") ? parseInt(document.getElementById("tokenPageSize").value, 10) : 25;
    const url = new URL("/admin/get_tokens", window.location.origin);
    // Her zaman tum kayitlari cek (silinen + pasif), ekranda filtrele
    url.searchParams.set("include_deleted", "true");
    if (search) url.searchParams.set("search", search);
    url.searchParams.set("page", String(_tokenPage));
    url.searchParams.set("page_size", String(pageSize));

    try {
        const response = await fetch(url.toString());
        const data = await response.json();
        if (!data.success) throw new Error(data.message || "Token yuklenemedi");

        loading.classList.remove("show");
        const tokens = data.tokens || [];
        // Varsayilan: sadece aktif (gizlenmeyen) tokenlar
        const visibleTokens = tokens.filter((t) => t.is_active);
        const hiddenTokens = tokens.filter((t) => !t.is_active || t.deleted_at);

        _tokenTotal = visibleTokens.length;

        const totalPages = pageSize ? Math.max(1, Math.ceil(_tokenTotal / pageSize)) : 1;
        const paginationInfo = document.getElementById("tokenPaginationInfo");
        const prevBtn = document.getElementById("tokenPrevPage");
        const nextBtn = document.getElementById("tokenNextPage");
        const pageSizeSelector = document.getElementById("tokenPageSize");
        
        const showPagination = totalPages > 1;
        
        if (pageSizeSelector) {
            pageSizeSelector.style.display = _tokenTotal > 10 ? "inline-block" : "none";
        }
        
        if (paginationInfo) {
            paginationInfo.textContent = _tokenTotal + " token, sayfa " + _tokenPage + " / " + totalPages;
            paginationInfo.style.display = showPagination ? "inline" : "none";
        }
        if (prevBtn) {
            prevBtn.disabled = _tokenPage <= 1;
            prevBtn.style.display = showPagination ? "inline-block" : "none";
        }
        if (nextBtn) {
            nextBtn.disabled = _tokenPage >= totalPages;
            nextBtn.style.display = showPagination ? "inline-block" : "none";
        }

        const deletedCount = hiddenTokens.length;
        const hiddenBtn = document.getElementById("showHiddenBtn");
        const hiddenCountEl = document.getElementById("hiddenCount");
        if (hiddenBtn && hiddenCountEl) {
            if (deletedCount > 0) {
                hiddenBtn.classList.add("visible");
                hiddenCountEl.textContent = deletedCount;
            } else {
                hiddenBtn.classList.remove("visible");
            }
        }

        if (visibleTokens.length === 0 && (!_showHidden || hiddenTokens.length === 0)) {
            tokensList.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>Token bulunamadi.</p></div>';
            return;
        }

        visibleTokens.forEach((token) => tokensList.appendChild(createTokenCard(token)));

        if (_showHidden && hiddenTokens.length > 0) {
            hiddenTokens.forEach((token) => tokensList.appendChild(createTokenCard(token)));
        }
    } catch (error) {
        loading.classList.remove("show");
        showAlert(error.message, "error");
    }
}

function createTokenCard(token) {
    const card = document.createElement("div");
    card.className = `token-card ${token.is_active ? "" : "inactive"}`;

    const safeUsername = escapeHtml(token.username);
    const safeFullName = escapeHtml(token.full_name);
    const safeTokenValue = typeof token.token === "string" ? token.token : "";
    const tokenPreview = safeTokenValue ? escapeHtml(`${safeTokenValue.substring(0, 60)}...`) : "Token yok";
    const safeAndroidId = escapeHtml(token.android_id_yeni || "Yok");
    const safeDeviceId = escapeHtml(token.device_id || "Yok");
    const safeLogoutReason = escapeHtml(token.logout_reason);

    const statusText = token.is_active ? "Aktif" : "Pasif";
    const statusClass = token.is_active ? "active" : "inactive";
    const fullNameDisplay = token.full_name ? `<div style="color: rgba(255, 255, 255, 0.6); font-size: 14px; margin-top: 5px;">${safeFullName}</div>` : "";
    const logoutReasonDisplay = token.logout_reason
        ? `<div style="background: rgba(231, 76, 60, 0.15); border: 1px solid rgba(231, 76, 60, 0.3); border-radius: 8px; padding: 12px; margin: 10px 0;"><div style="color: #e74c3c; font-weight: 600; font-size: 13px; margin-bottom: 5px;"><i class="fas fa-exclamation-circle"></i> Cikis Yapildi</div><div style="color: rgba(255, 255, 255, 0.8); font-size: 12px;">${safeLogoutReason}</div>${token.logout_time ? `<div style="color: rgba(255, 255, 255, 0.5); font-size: 11px; margin-top: 5px;">${escapeHtml(new Date(token.logout_time).toLocaleString("tr-TR"))}</div>` : ""}</div>`
        : "";

    card.innerHTML = `<div class="token-header"><div><span class="token-username"><i class="fab fa-instagram"></i> @${safeUsername}</span>${fullNameDisplay}</div><span class="token-status ${statusClass}">${statusText}</span></div>${logoutReasonDisplay}<div class="token-info"><strong>Token:</strong><div class="token-value">${tokenPreview}</div></div><div class="token-info"><strong>Android ID:</strong> <span class="token-value" style="display: inline-block;">${safeAndroidId}</span></div><div class="token-info"><strong>Device ID:</strong> <span class="token-value" style="display: inline-block;">${safeDeviceId}</span></div><div class="token-info"><strong>Eklenme Tarihi:</strong> ${token.added_at ? escapeHtml(new Date(token.added_at).toLocaleString("tr-TR")) : "Bilinmiyor"}</div><div class="token-actions"></div>`;

    const actionsDiv = card.querySelector(".token-actions");

    const editBtn = document.createElement("button");
    editBtn.className = "btn";
    editBtn.innerHTML = '<i class="fas fa-edit"></i> Duzenle';
    editBtn.addEventListener("click", () => editToken(token.username));
    actionsDiv.appendChild(editBtn);

    const exportBtn = document.createElement("button");
    exportBtn.className = "btn";
    exportBtn.innerHTML = '<i class="fas fa-download"></i> Dışarı Aktar';
    exportBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(token, null, 4));
        const dlAnchorElem = document.createElement('a');
        dlAnchorElem.setAttribute("href", dataStr);
        dlAnchorElem.setAttribute("download", `${token.username}_token.json`);
        document.body.appendChild(dlAnchorElem);
        dlAnchorElem.click();
        dlAnchorElem.remove();
        showAlert(`@${token.username} için token başarıyla dışarı aktarıldı.`, "success");
    });
    actionsDiv.appendChild(exportBtn);
    const lastFail = token.last_relogin_failed_at;
    let isCooldown = false;
    let remaining = 0;
    if (lastFail) {
        const lastFailTs = parseFloat(lastFail);
        const nowTs = Date.now() / 1000;
        const elapsed = nowTs - lastFailTs;
        if (elapsed < 180) {
            isCooldown = true;
            remaining = Math.ceil(180 - elapsed);
        }
    }

    const reloginBtn = document.createElement("button");
    reloginBtn.className = "btn";
    if (isCooldown) {
        reloginBtn.disabled = true;
        reloginBtn.style.opacity = "0.5";
        reloginBtn.style.cursor = "not-allowed";
        reloginBtn.innerHTML = `<i class="fas fa-hourglass-half"></i> Bekleyin (${remaining}s)`;
        
        const timerId = setInterval(() => {
            remaining--;
            if (remaining <= 0) {
                clearInterval(timerId);
                reloginBtn.disabled = false;
                reloginBtn.style.opacity = "";
                reloginBtn.style.cursor = "";
                reloginBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Tekrar Giris Yap';
            } else {
                reloginBtn.innerHTML = `<i class="fas fa-hourglass-half"></i> Bekleyin (${remaining}s)`;
            }
        }, 1000);
    } else {
        reloginBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Tekrar Giris Yap';
    }
    reloginBtn.addEventListener("click", () => reloginToken(token.username));
    actionsDiv.appendChild(reloginBtn);

    const toggleBtn = document.createElement("button");
    toggleBtn.className = "btn";
    toggleBtn.innerHTML = `<i class="fas fa-toggle-${token.is_active ? "off" : "on"}"></i> ${token.is_active ? "Pasif Yap" : "Aktif Yap"}`;
    toggleBtn.addEventListener("click", () => toggleToken(token.username));
    actionsDiv.appendChild(toggleBtn);

    const validateBtn = document.createElement("button");
    validateBtn.className = "btn";
    validateBtn.innerHTML = '<i class="fas fa-check-circle"></i> Dogrula';
    validateBtn.addEventListener("click", () => validateToken(token.username));
    actionsDiv.appendChild(validateBtn);

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "btn";
    deleteBtn.innerHTML = '<i class="fas fa-trash"></i> Sil';
    deleteBtn.addEventListener("click", () => deleteToken(token.username));
    actionsDiv.appendChild(deleteBtn);

    if (token.deleted_at) {
        const restoreBtn = document.createElement("button");
        restoreBtn.className = "btn";
        restoreBtn.innerHTML = '<i class="fas fa-undo"></i> Geri Al';
        restoreBtn.addEventListener("click", () => restoreToken(token.username));
        actionsDiv.appendChild(restoreBtn);
    }

    return card;
}

async function restoreToken(username) {
    try {
        const data = await postJson("/admin/restore_token", { username });
        if (data.success) {
            showAlert(data.message, "success");
            loadTokens();
            loadStats();
            return;
        }
        showAlert(data.message, "error");
    } catch (error) {
        showAlert("Geri alma basarisiz: " + error.message, "error");
    }
}

async function toggleToken(username) {
    try {
        const response = await fetch("/admin/toggle_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username }),
        });

        const data = await response.json();
        if (data.success) {
            showAlert(data.message, "success");
            loadStats();
            loadTokens();
            return;
        }
        showAlert(data.message, "error");
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
}

async function validateToken(username) {
    showAlert("Token dogrulaniyor...", "info");

    try {
        const response = await fetch("/admin/validate_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username }),
        });

        const data = await response.json();
        if (data.success) {
            if (data.is_valid) {
                showResultModal("success", "Token Geçerli!", `@${username} için token geçerli ve aktif durumda.`);
            } else {
                showResultModal("error", "Token Geçersiz!", `@${username} için token geçersiz veya süresi dolmuş.`);
                loadStats();
                loadTokens();
            }
            return;
        }
        showAlert(data.message, "error");
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
}

async function deleteToken(username) {
    if (!confirm(`⚠️ ${username} icin tokeni silmek istediginizden emin misiniz?`)) {
        return;
    }

    try {
        const response = await fetch("/admin/delete_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username }),
        });

        const data = await response.json();
        if (data.success) {
            showAlert(data.message, "success");
            loadStats();
            loadTokens();
            return;
        }
        showAlert(data.message, "error");
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
}

let _reloginUsername = null;
let _reloginMissing = [];

const RELOGIN_FIELD_LABELS = {
    password: "Sifre",
    device_id: "Device ID",
    user_agent: "User Agent",
    android_id: "Android ID",
};

function openReloginFieldsModal(username, missing) {
    _reloginUsername = username;
    _reloginMissing = missing || [];
    const modal = document.getElementById("reloginFieldsModal");
    const msgEl = document.getElementById("reloginFieldsMessage");
    const formEl = document.getElementById("reloginFieldsForm");
    if (!formEl) return;
    if (msgEl) msgEl.textContent = "@" + username + " icin asagidaki alanlar eksik. Girilen degerler hesaba kaydedilir ve tekrar giris yapilir.";
    formEl.innerHTML = "";
    const inputStyle = "width: 100%; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.08); color: #fff; font-size: 14px;";
    _reloginMissing.forEach((key) => {
        const label = document.createElement("label");
        label.style.cssText = "display: block; color: rgba(255,255,255,0.9); margin-bottom: 6px; font-size: 14px;";
        label.textContent = RELOGIN_FIELD_LABELS[key] || key;
        formEl.appendChild(label);
        const isTextarea = key === "user_agent";
        const input = isTextarea ? document.createElement("textarea") : document.createElement("input");
        input.id = "relogin_field_" + key;
        input.setAttribute("data-field", key);
        if (!isTextarea) input.type = key === "password" ? "password" : "text";
        input.placeholder = key === "password" ? "Sifrenizi girin" : RELOGIN_FIELD_LABELS[key] + " girin";
        input.style.cssText = inputStyle;
        if (isTextarea) input.rows = 3;
        input.onkeydown = (e) => { if (e.key === "Enter" && key !== "user_agent") submitReloginFields(); };
        formEl.appendChild(input);
    });
    if (modal) modal.classList.add("show");
    const first = formEl.querySelector("input, textarea");
    if (first) first.focus();
}

function closeReloginFieldsModal() {
    _reloginUsername = null;
    _reloginMissing = [];
    const modal = document.getElementById("reloginFieldsModal");
    if (modal) modal.classList.remove("show");
}

async function reloginToken(username, overrides) {
    const hasOverrides = overrides && typeof overrides === "object" && Object.keys(overrides).length > 0;
    if (!hasOverrides && !confirm(`@${username} icin tekrar giris yapilacak ve token yenilenecek. Devam edilsin mi?`)) {
        return;
    }

    if (!hasOverrides) {
        showAlert("Tekrar giris yapiliyor...", "info");
    }

    try {
        const payload = { username };
        if (overrides && typeof overrides === "object") {
            if (overrides.password != null) payload.password = overrides.password;
            if (overrides.device_id != null) payload.device_id = overrides.device_id;
            if (overrides.user_agent != null) payload.user_agent = overrides.user_agent;
            if (overrides.android_id != null) payload.android_id = overrides.android_id;
        } else if (typeof overrides === "string") {
            payload.password = overrides;
        }
        const response = await fetch("/admin/relogin_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (data.success) {
            closeReloginFieldsModal();
            showAlert(data.message, "success");
            loadStats();
            loadTokens();
            return;
        }
        if (data.code === "COOLDOWN_ACTIVE") {
            closeReloginFieldsModal();
            showResultModal("cooldown", "Giriş Engellendi (3 Dakika)", data.message);
            loadTokens();
            return;
        }
        if (data.code === "FIELDS_REQUIRED" && data.missing && data.missing.length > 0) {
            openReloginFieldsModal(username, data.missing);
            return;
        }
        closeReloginFieldsModal();
        showResultModal("warning", "Giriş Başarısız", "Giriş işlemi başarısız oldu. Hesap doğrulamaya (SMS, e-posta veya şüpheli hareket bildirimine) düşmüş olabilir. Lütfen telefonunuzdan Instagram uygulamasını açarak bu durumu kontrol edin ve çözün. 3 dakika boyunca tekrar giriş yapmanıza izin verilmeyecektir.");
        loadTokens();

    } catch (error) {
        showAlert("Bir hata olustu: " + error.message, "error");
    }
}

async function submitReloginFields() {
    if (!_reloginUsername || !_reloginMissing.length) {
        closeReloginFieldsModal();
        return;
    }
    const overrides = {};
    let allFilled = true;
    _reloginMissing.forEach((key) => {
        const el = document.getElementById("relogin_field_" + key);
        const val = el ? el.value.trim() : "";
        if (!val) allFilled = false;
        overrides[key] = val;
    });
    if (!allFilled) {
        showAlert("Lutfen tum eksik alanlari doldurun.", "error");
        return;
    }
    closeReloginFieldsModal();
    showAlert("Kaydediliyor ve tekrar giris yapiliyor...", "info");
    await reloginToken(_reloginUsername, overrides);
}

async function editToken(username) {
    try {
        const response = await fetch("/admin/get_tokens?username=" + encodeURIComponent(username));
        const data = await response.json();
        if (!data.success) {
            showAlert("Token yuklenemedi", "error");
            return;
        }

        const token = data.tokens && data.tokens[0];
        if (!token) {
            showAlert("Token bulunamadi", "error");
            return;
        }

        document.getElementById("edit_username").value = token.username;
        document.getElementById("edit_username_display").value = `@${token.username}${token.full_name ? ` (${token.full_name})` : ""}`;
        document.getElementById("edit_token").value = token.token;
        document.getElementById("edit_android_id").value = token.android_id_yeni;
        document.getElementById("edit_device_id").value = token.device_id || "";
        document.getElementById("edit_password").value = token.password || "";
        document.getElementById("edit_user_agent").value = token.user_agent;
        document.getElementById("editModal").classList.add("show");
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
}

function closeEditModal() {
    document.getElementById("editModal").classList.remove("show");
}

document.getElementById("addTokenForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = {
        token: document.getElementById("token").value.trim(),
        android_id: document.getElementById("android_id").value.trim(),
        device_id: document.getElementById("device_id").value.trim(),
        user_agent: document.getElementById("user_agent").value.trim(),
        password: document.getElementById("password").value.trim(),
        is_active: true,
        added_at: new Date().toISOString(),
    };

    if (!formData.token || !formData.android_id || !formData.device_id || !formData.user_agent || !formData.password) {
        showAlert("Lutfen tum alanlari doldurun!", "error");
        return;
    }

    showAlert("Token dogrulaniyor ve kullanici adi aliniyor...", "info");

    try {
        const response = await fetch("/admin/add_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData),
        });

        const data = await response.json();
        if (data.success) {
            document.getElementById("addTokenForm").reset();
            loadStats();
            loadTokens();
            showResultModal("success", "Token Başarıyla Bağlandı!", `@${data.username}${data.full_name ? ` (${data.full_name})` : ""} hesabı için token başarıyla eklendi ve aktif edildi.`);
            return;
        }
        showAlert(data.message, "error");
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
});

document.getElementById("editModal").addEventListener("click", (event) => {
    if (event.target.id === "editModal") {
        closeEditModal();
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeEditModal();
        closeSuccessModal();
    }
});

let _resultTimer = null;
function showResultModal(type, title, detail) {
    const modal = document.getElementById("successModal");
    const iconEl = document.getElementById("resultIcon");
    const iconInner = document.getElementById("resultIconInner");
    const titleEl = document.getElementById("resultTitle");
    const detailEl = document.getElementById("resultDetail");
    const btnEl = document.getElementById("resultCloseBtn");

    const isSuccess = type === "success";
    const isWarning = type === "warning" || type === "cooldown";
    
    let color = isSuccess ? "#2ecc71" : "#e74c3c";
    if (isWarning) {
        color = "#f39c12"; // Orange warning color
    }
    
    const colorAlpha15 = isSuccess ? "rgba(39,174,96,0.15)" : (isWarning ? "rgba(243,156,18,0.15)" : "rgba(231,76,60,0.15)");
    const colorAlpha40 = isSuccess ? "rgba(39,174,96,0.4)" : (isWarning ? "rgba(243,156,18,0.4)" : "rgba(231,76,60,0.4)");

    iconEl.style.background = colorAlpha15;
    iconEl.style.borderColor = colorAlpha40;
    iconInner.style.color = color;
    
    if (isSuccess) {
        iconInner.className = "fas fa-check";
    } else if (isWarning) {
        iconInner.className = "fas fa-exclamation-triangle";
    } else {
        iconInner.className = "fas fa-times";
    }
    
    titleEl.style.color = color;
    titleEl.textContent = title;
    detailEl.textContent = detail;
    btnEl.style.background = colorAlpha15;
    btnEl.style.borderColor = colorAlpha40;
    btnEl.style.color = color;

    modal.classList.add("show");
    if (_resultTimer) clearTimeout(_resultTimer);
    if (!isWarning) {
        _resultTimer = setTimeout(() => closeSuccessModal(), 4000);
    }
}

function closeSuccessModal() {
    document.getElementById("successModal").classList.remove("show");
    if (_resultTimer) {
        clearTimeout(_resultTimer);
        _resultTimer = null;
    }
}

document.getElementById("editTokenForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("edit_username").value;
    const formData = {
        username,
        token: document.getElementById("edit_token").value.trim(),
        android_id: document.getElementById("edit_android_id").value.trim(),
        device_id: document.getElementById("edit_device_id").value.trim(),
        password: document.getElementById("edit_password").value.trim(),
        user_agent: document.getElementById("edit_user_agent").value.trim(),
    };

    if (!formData.token || !formData.android_id || !formData.device_id || !formData.user_agent || !formData.password) {
        showAlert("Lutfen tum alanlari doldurun!", "error");
        return;
    }

    showAlert("Token guncelleniyor...", "info");

    try {
        const response = await fetch("/admin/update_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData),
        });
        const data = await response.json();
        if (data.success) {
            showAlert(data.message, "success");
            closeEditModal();
            loadStats();
            loadTokens();
            return;
        }
        showAlert(data.message, "error");
    } catch (error) {
        showAlert(`Bir hata olustu: ${error.message}`, "error");
    }
});

document.getElementById("addExemptionForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const postLink = document.getElementById("exemption_post_link").value.trim();
    const username = document.getElementById("exemption_username").value.trim().replace(/^@+/, "");

    if (!postLink || !username) {
        showAlert("Paylasim linki ve kullanici adi zorunlu", "error");
        return;
    }

    try {
        const data = await addExemptionAdmin(postLink, username);
        showAlert(data.message, "success");
        document.getElementById("addExemptionForm").reset();
        loadExemptions();
    } catch (error) {
        showAlert(error.message, "error");
    }
});

// ============================================
// ============================================
// AUTOMATION MANAGEMENT (BETA)
// ============================================

async function fetchGlobalAutomationStatus() {
    const btn = document.getElementById("globalAutomationToggleBtn");
    if (!btn) return;
    try {
        const res = await fetch("/admin/get_global_automation_status");
        const data = await res.json();
        if (data.success) {
            updateGlobalAutomationBtn(data.is_active);
        }
    } catch (e) {
        console.error("Global otomasyon durumu alinamadi", e);
    }
}

function updateGlobalAutomationBtn(isActive) {
    const btn = document.getElementById("globalAutomationToggleBtn");
    if (!btn) return;
    const span = btn.querySelector("span");
    const icon = btn.querySelector("i");
    if (isActive) {
        btn.className = "btn btn-success";
        span.textContent = "Global Otomasyon: AKTİF";
        icon.className = "fas fa-toggle-on";
    } else {
        btn.className = "btn btn-danger";
        span.textContent = "Global Otomasyon: PASİF";
        icon.className = "fas fa-toggle-off";
    }
}

async function toggleGlobalAutomation() {
    const btn = document.getElementById("globalAutomationToggleBtn");
    if(!btn) return;
    btn.disabled = true;
    try {
        const res = await postJson("/admin/toggle_global_automation", {});
        if (res.success) {
            updateGlobalAutomationBtn(res.is_active);
            showAlert(res.message, "success");
        } else {
            showAlert(res.message, "error");
        }
    } catch (e) {
        showAlert("Hata: " + e.message, "error");
    } finally {
        btn.disabled = false;
    }
}
window.toggleGlobalAutomation = toggleGlobalAutomation;

async function fetchGlobalAutomationSettings() {
    try {
        const res = await fetch("/admin/get_global_automation_settings");
        const data = await res.json();
        if (data.success && data.settings) {
            const s = data.settings;
            const timeEl = document.getElementById("global_auto_times");
            if(timeEl) timeEl.value = s.times || "23:59";
            
            const sendEl = document.getElementById("global_send_group");
            if(sendEl) sendEl.checked = s.send_to_group !== false;
            
            const tempEl = document.getElementById("global_auto_template");
            if(tempEl) tempEl.value = s.template || "@everyone merhaba arkadaşlar eksik listesindeki tüm arkadaşlarımıza dm yazdık dönüş yapmayanları aramızdan çıkarmak durumunda kalacağız.";
            
            const dmToggleEl = document.getElementById("global_send_dm_to_missing");
            if(dmToggleEl) dmToggleEl.checked = s.send_dm_to_missing !== false;
            
            const dmTempEl = document.getElementById("global_dm_template");
            if(dmTempEl) dmTempEl.value = s.dm_template || "Merhaba, {grup_ismi} grubumuzda eksiğiniz bulunmaktadır. Lütfen dönüş yapalım..";
            
            const adminNotifyEl = document.getElementById("global_admin_notify_template");
            if(adminNotifyEl) adminNotifyEl.value = s.admin_notify_template || "✅ Otomasyon tamamlandı!\n\n📌 Grup: {grup_ismi}\n🔗 Post: {post_url}\n📅 Paylaşım Tarihi: {post_tarihi}\n\n👥 Toplam üye: {toplam_uye}\n❌ Eksik: {eksik_sayisi}\n⏰ Saat: {saat}";
        }
    } catch (e) {
        console.error("Global otomasyon ayarlari alinamadi", e);
    }
}

async function saveGlobalAutomationSettings() {
    const timeEl = document.getElementById("global_auto_times");
    const sendEl = document.getElementById("global_send_group");
    const tempEl = document.getElementById("global_auto_template");
    const dmToggleEl = document.getElementById("global_send_dm_to_missing");
    const dmTempEl = document.getElementById("global_dm_template");
    const adminNotifyEl = document.getElementById("global_admin_notify_template");
    
    if(!timeEl || !sendEl || !tempEl) return;
    
    try {
        const res = await fetch('/admin/save_global_automation_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                times: timeEl.value,
                send_to_group: sendEl.checked,
                template: tempEl.value,
                send_dm_to_missing: dmToggleEl ? dmToggleEl.checked : true,
                dm_template: dmTempEl ? dmTempEl.value : "Merhaba, {grup_ismi} grubumuzda eksiğiniz bulunmaktadır. Lütfen dönüş yapalım..",
                admin_notify_template: adminNotifyEl ? adminNotifyEl.value : ""
            })
        });
        const data = await res.json();
        if (data.success) {
            showAlert('Ayarlar başarıyla kaydedildi!', 'success');
        } else {
            showAlert(data.message || 'Hata oluştu.', 'error');
        }
    } catch (e) {
        console.error(e);
        showAlert('Bir hata oluştu.', 'error');
    }
}

async function testAdminNotification(threadId, groupName) {
    if (!confirm(`${groupName} grubu için kendinize test bildirimi göndermek istiyor musunuz? (Kaydedilmiş bildirim şablonunuzu kullanır)`)) return;
    
    const notifyUsername = (document.getElementById(`auto_notify_${threadId}`) || {}).value || 'seghob';
    
    try {
        const res = await fetch('/admin/test_admin_notification', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                thread_id: threadId,
                group_name: groupName,
                notify_username: notifyUsername.trim().replace(/^@/, '')
            })
        });
        const data = await res.json();
        if (data.success) {
            showAlert('Test bildirimi başarıyla gönderildi!', 'success');
        } else {
            showAlert(data.message || 'Hata oluştu.', 'error');
        }
    } catch (e) {
        console.error(e);
        showAlert('Bir hata oluştu.', 'error');
    }
}
window.saveGlobalAutomationSettings = saveGlobalAutomationSettings;

function toggleAutomationPanel() {
    const body = document.getElementById('automationBody');
    const chevron = document.getElementById('automationChevron');
    if (!body || !chevron) return;
    
    const isCollapsed = body.classList.contains('collapsed');
    if (isCollapsed) {
        closeAllPanels("automationBody");
        slideDown(body);
        chevron.classList.add('rotated');
        fetchGlobalAutomationStatus();
        fetchGlobalAutomationSettings();
    } else {
        slideUp(body);
        chevron.classList.remove('rotated');
    }
}

async function loadAutomationGroups() {
    const loading = document.getElementById('automationLoading');
    const btn = document.getElementById('loadAutomationBtn');
    const status = document.getElementById('automationStatus');
    const list = document.getElementById('automationList');
    
    if (!loading || !btn || !status || !list) return;

    loading.style.display = 'block';
    btn.disabled = true;
    list.innerHTML = '';
    
    try {
        const autoRes = await fetch('/admin/get_automations');
        const autoData = await autoRes.json();
        const savedAutos = autoData.success ? (autoData.automations || {}) : {};

        const groupRes = await fetch('/admin/get_groups');
        const groupData = await groupRes.json();
        
        if (groupData.success) {
            const groups = groupData.groups || [];
            if (groups.length === 0) {
                list.innerHTML = `<div style="color:#aaa; text-align:center; padding: 20px;">Sistemde çekilecek grup bulunamadı.</div>`;
            } else {
                groups.forEach(g => {
                    const threadId = g.id;
                    const groupName = g.name || 'İsimsiz Grup';
                    const saved = savedAutos[threadId] || {};
                    const isChecked = saved.is_active ? 'checked' : '';
                    
                    const card = document.createElement('div');
                    card.className = 'exemption-card';
                    card.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <strong style="color:#f0f0f0; font-size:15px;"><i class="fas fa-users me-2" style="color:#a78bfa;"></i> ${escapeHtml(groupName)}</strong>
                            <label class="toggle-switch" style="transform: scale(0.85); display: inline-block;">
                                <input type="checkbox" id="auto_toggle_${threadId}" ${isChecked}>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div style="font-size:12px; color:#a0aec0; margin-bottom:12px; word-break:break-all;">Üye: ${g.member_count || '?'} kişi</div>
                        <div style="margin-bottom:12px;">
                            <label style="color:rgba(255,255,255,0.6); font-size:13px; display:block; margin-bottom:5px;"><i class="fas fa-filter me-1"></i> Kontrol Yöntemi:</label>
                            <select id="auto_method_${threadId}" style="background:rgba(0,0,0,0.2); border:1px solid rgba(196,149,106,0.3); color:#fff; padding:6px 12px; border-radius:8px; width:100%; font-size:13px; outline:none;">
                                <option value="all_members" style="background:#16110d; color:#fff;" ${saved.control_method === 'all_members' || !saved.control_method ? 'selected' : ''}>Tüm Üyeler Arası Kontrol</option>
                                <option value="post_senders" style="background:#16110d; color:#fff;" ${saved.control_method === 'post_senders' ? 'selected' : ''}>Sadece Paylaşım Yapanlar Arası Kontrol</option>
                            </select>
                        </div>
                        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                            <label style="color:rgba(255,255,255,0.6); font-size:13px;"><i class="fas fa-bell me-1"></i> Bildirim:</label>
                            <input type="text" id="auto_notify_${threadId}" value="${saved.notify_username || 'seghob'}" placeholder="Kullanıcı adı" style="background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.1); color:#fff; padding:6px 12px; border-radius:8px; width:120px;">
                            <button type="button" class="btn btn-sm btn-success" onclick="saveAutomation('${threadId}', '${escapeHtml(groupName)}')">
                                <i class="fas fa-save me-1"></i> Kaydet
                            </button>
                            <button type="button" class="btn btn-sm" style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.4);color:#f87171;" onclick="triggerAutomation('${threadId}', '${escapeHtml(groupName)}')">
                                <i class="fas fa-bolt me-1"></i> Tetikle
                            </button>
                            <button type="button" class="btn btn-sm" style="background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.3);color:#fbbf24;" onclick="unsendMessages('${threadId}', '${escapeHtml(groupName)}')">
                                <i class="fas fa-undo me-1"></i> Geri Al
                            </button>
                            <button type="button" class="btn btn-sm" style="background:rgba(167,139,250,0.15);border:1px solid rgba(167,139,250,0.4);color:#c4b5fd;" onclick="testAdminNotification('${threadId}', '${escapeHtml(groupName)}')">
                                <i class="fas fa-paper-plane me-1"></i> Test Gönder
                            </button>
                        </div>
                    `;
                    list.appendChild(card);
                });
            }
        } else {
            showAlert(groupData.message || 'Gruplar çekilemedi.', 'error');
        }
    } catch (e) {
        console.error(e);
        showAlert('Otomasyon verileri yüklenirken hata oluştu.', 'error');
    } finally {
        loading.style.display = 'none';
        btn.disabled = false;
        status.style.display = 'inline-flex';
        setTimeout(() => status.style.display = 'none', 3000);
    }
}

async function saveAutomation(threadId, groupName) {
    const isActive = document.getElementById(`auto_toggle_${threadId}`).checked;
    const notifyUsername = (document.getElementById(`auto_notify_${threadId}`) || {}).value || 'seghob';
    const controlMethod = (document.getElementById(`auto_method_${threadId}`) || {}).value || 'all_members';
    
    try {
        const res = await fetch('/admin/save_automation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                thread_id: threadId,
                is_active: isActive,
                group_name: groupName,
                notify_username: notifyUsername.trim().replace(/^@/, ''),
                control_method: controlMethod
            })
        });
        const data = await res.json();
        if (data.success) {
            showAlert(`[${groupName}] otomasyonu ${isActive ? 'aktif' : 'pasif'} olarak kaydedildi!`, 'success');
        } else {
            showAlert(data.message || 'Kaydedilemedi.', 'error');
        }
    } catch (e) {
        console.error(e);
        showAlert('Hata olustu.', 'error');
    }
}

async function liveTestAutomation() {
    if (!confirm(`Sistemde aktif olan tüm gruplar için ŞU AN Canlı Test (Sadece bildirim, mesaj atılmaz) başlatılacaktır. Emin misiniz?`)) return;
    try {
        const res = await fetch('/admin/live_test_automation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.success) {
            showAlert(data.message, 'success');
        } else {
            showAlert(data.message || 'Hata oluştu.', 'error');
        }
    } catch (e) {
        console.error(e);
        showAlert('Bir hata oluştu.', 'error');
    }
}

async function triggerAutomation(threadId, groupName) {
    if (!confirm(`⚡ [${groupName}] grubu için otomasyonu HEMEN tetiklemek istiyor musunuz?\nBu işlem gruba DM gönderecek!`)) return;

    try {
        showAlert('Otomasyon tetikleniyor...', 'info');
        const res = await fetch('/admin/trigger_automation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: threadId })
        });
        const data = await res.json();
        if (data.success) {
            showAlert('✅ Otomasyon arka planda çalışıyor. Flask loglarını kontrol edin.', 'success');
        } else {
            showAlert(data.message || 'Tetiklenemedi.', 'error');
        }
    } catch (e) {
        console.error(e);
        showAlert('Tetikleme hatası: ' + e.message, 'error');
    }
}

async function unsendMessages(threadId, groupName) {
    if (!confirm(`🗑️ [${groupName}] grubuna atılan BOT mesajlarını geri almak istiyor musunuz?\nSon 30 bot mesajı silinecek.`)) return;

    try {
        showAlert('Mesajlar geri alınıyor...', 'info');
        const res = await fetch('/admin/unsend_messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: threadId })
        });
        const data = await res.json();
        if (data.success) {
            showAlert(`✅ ${data.message}`, 'success');
        } else {
            showAlert(data.message || 'Geri alınamadı.', 'error');
        }
    } catch (e) {
        console.error(e);
        showAlert('Hata: ' + e.message, 'error');
    }
}

window.toggleToken = toggleToken;
window.validateToken = validateToken;
window.deleteToken = deleteToken;
window.reloginToken = reloginToken;
window.editToken = editToken;
window.closeEditModal = closeEditModal;
window.removeExemption = removeExemption;
window.removeExemptionsByLink = removeExemptionsByLink;
window.toggleExemptionsPanel = toggleExemptionsPanel;
window.toggleAddTokenPanel = toggleAddTokenPanel;
window.toggleTokensListPanel = toggleTokensListPanel;
window.toggleHiddenTokens = toggleHiddenTokens;
window.toggleAuditPanel = toggleAuditPanel;
window.toggleGlobalExemptionPanel = toggleGlobalExemptionPanel;
window.toggleAutomationPanel = toggleAutomationPanel;
window.loadAutomationGroups = loadAutomationGroups;
window.saveAutomation = saveAutomation;
window.triggerAutomation = triggerAutomation;
window.unsendMessages = unsendMessages;
window.closeSuccessModal = closeSuccessModal;
window.closeReloginFieldsModal = closeReloginFieldsModal;
window.submitReloginFields = submitReloginFields;

loadStats();
document.getElementById("tokenSearch") && document.getElementById("tokenSearch").addEventListener("input", () => { _tokenPage = 1; loadTokens(); });
document.getElementById("tokenPageSize") && document.getElementById("tokenPageSize").addEventListener("change", () => { _tokenPage = 1; loadTokens(); });
document.getElementById("tokenPrevPage") && document.getElementById("tokenPrevPage").addEventListener("click", () => { if (_tokenPage > 1) { _tokenPage--; loadTokens(); } });
document.getElementById("tokenNextPage") && document.getElementById("tokenNextPage").addEventListener("click", () => { _tokenPage++; loadTokens(); });

document.getElementById("exemptionSearch") && document.getElementById("exemptionSearch").addEventListener("input", () => { _exemptionPage = 1; loadExemptions(); });
document.getElementById("exemptionPageSize") && document.getElementById("exemptionPageSize").addEventListener("change", () => { _exemptionPage = 1; loadExemptions(); });
document.getElementById("exemptionPrevPage") && document.getElementById("exemptionPrevPage").addEventListener("click", () => { if (_exemptionPage > 1) { _exemptionPage--; loadExemptions(); } });
document.getElementById("exemptionNextPage") && document.getElementById("exemptionNextPage").addEventListener("click", () => { _exemptionPage++; loadExemptions(); });

setInterval(() => {
    loadStats();
    const tokensBody = document.getElementById("tokensListBody");
    if (tokensBody && !tokensBody.classList.contains("collapsed")) loadTokens();
    const exemptBody = document.getElementById("exemptionsSectionBody");
    if (exemptBody && !exemptBody.classList.contains("collapsed")) loadExemptions();
    const globalExemptBody = document.getElementById("globalExemptionBody");
    if (globalExemptBody && !globalExemptBody.classList.contains("collapsed")) loadGlobalExemptions();
}, 30000);

async function handleImportJson(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append("file", file);
    
    showAlert("Tokenler içeri aktarılıyor...", "info");
    try {
        const response = await fetch("/admin/import_tokens", {
            method: "POST",
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            showAlert(data.message, "success");
            loadTokens();
            loadStats();
        } else {
            showAlert(data.message || "İçeri aktarma başarısız oldu.", "error");
        }
    } catch (e) {
        showAlert("Hata: " + e.message, "error");
    }
    event.target.value = "";
}
window.handleImportJson = handleImportJson;


// ── Yorum Spam & Puanlama Raporu İşlevleri ──
function toggleSpamReportPanel() {
    const body = document.getElementById("spamReportBody");
    const chevron = document.getElementById("spamReportChevron");
    if (!body || !chevron) return;
    
    if (body.classList.contains("collapsed")) {
        slideDown(body);
        chevron.classList.add("rotated");
        populateSpamReportGroupsDropdown();
    } else {
        slideUp(body);
        chevron.classList.remove("rotated");
    }
}
window.toggleSpamReportPanel = toggleSpamReportPanel;

function toggleSpamDropdown() {
    const section = document.getElementById("spamReportSection");
    const dropdown = document.getElementById("spamReportGroupDropdown");
    const menu = document.getElementById("spamReportDropdownMenu");
    const trigger = document.getElementById("spamReportDropdownTrigger");
    if (menu && trigger) {
        menu.classList.toggle("show");
        trigger.classList.toggle("active");
        if (dropdown) {
            dropdown.classList.toggle("active");
        }
        if (section) {
            section.classList.toggle("active-dropdown");
        }
    }
}
window.toggleSpamDropdown = toggleSpamDropdown;

function filterSpamDropdown(val) {
    const query = val.toLowerCase().trim();
    const options = document.querySelectorAll("#spamReportGroupDropdownOptions .dropdown-option");
    options.forEach(opt => {
        const text = opt.textContent.toLowerCase();
        if (text.includes(query)) {
            opt.style.display = "flex";
        } else {
            opt.style.display = "none";
        }
    });
}
window.filterSpamDropdown = filterSpamDropdown;

function selectSpamGroup(id, name) {
    const section = document.getElementById("spamReportSection");
    const dropdown = document.getElementById("spamReportGroupDropdown");
    const input = document.getElementById("spamReportGroupSelect");
    const textSpan = document.getElementById("spamReportGroupDropdownText");
    const menu = document.getElementById("spamReportDropdownMenu");
    const trigger = document.getElementById("spamReportDropdownTrigger");
    
    if (input && textSpan && menu && trigger) {
        input.value = id;
        textSpan.textContent = name;
        
        // Highlight selected
        const options = document.querySelectorAll("#spamReportGroupDropdownOptions .dropdown-option");
        options.forEach(opt => {
            if (opt.getAttribute("data-id") === id) {
                opt.classList.add("selected");
            } else {
                opt.classList.remove("selected");
            }
        });
        
        menu.classList.remove("show");
        trigger.classList.remove("active");
        if (dropdown) {
            dropdown.classList.remove("active");
        }
        if (section) {
            section.classList.remove("active-dropdown");
        }
        
        // Trigger onchange event
        input.dispatchEvent(new Event("change"));
    }
}
window.selectSpamGroup = selectSpamGroup;

// Close dropdown on click outside
document.addEventListener("click", (e) => {
    const section = document.getElementById("spamReportSection");
    const dropdown = document.getElementById("spamReportGroupDropdown");
    if (dropdown && !dropdown.contains(e.target)) {
        const menu = document.getElementById("spamReportDropdownMenu");
        const trigger = document.getElementById("spamReportDropdownTrigger");
        if (menu) menu.classList.remove("show");
        if (trigger) trigger.classList.remove("active");
        dropdown.classList.remove("active");
        if (section) {
            section.classList.remove("active-dropdown");
        }
    }
});

async function populateSpamReportGroupsDropdown() {
    const container = document.getElementById("spamReportGroupDropdownOptions");
    const select = document.getElementById("spamReportGroupSelect");
    const textSpan = document.getElementById("spamReportGroupDropdownText");
    if (!container || !select || !textSpan) return;
    
    container.innerHTML = "";
    
    try {
        const response = await fetch("/admin/get_groups");
        const data = await response.json();
        if (data.success && data.groups) {
            data.groups.forEach(g => {
                const div = document.createElement("div");
                div.className = "dropdown-option";
                div.setAttribute("data-id", g.id);
                div.textContent = g.name || 'İsimsiz Grup';
                
                // Add select styling if this is the active value
                if (select.value === g.id) {
                    div.classList.add("selected");
                    textSpan.textContent = g.name || 'İsimsiz Grup';
                }
                
                div.onclick = () => selectSpamGroup(g.id, g.name || 'İsimsiz Grup');
                container.appendChild(div);
            });
        }
    } catch (e) {
        console.error("Grup listesi getirme hatası:", e);
    }
}
window.populateSpamReportGroupsDropdown = populateSpamReportGroupsDropdown;

async function loadGroupSpamReport() {
    const select = document.getElementById("spamReportGroupSelect");
    const loading = document.getElementById("spamReportLoading");
    const wrapper = document.getElementById("spamReportTableWrapper");
    const tbody = document.getElementById("spamReportTableBody");
    const emptyMsg = document.getElementById("spamReportEmptyMsg");
    const searchWrapper = document.getElementById("spamReportMemberSearchWrapper");
    const searchInput = document.getElementById("spamReportMemberSearch");
    
    if (!select || !loading || !wrapper || !tbody || !emptyMsg) return;
    
    if (searchWrapper) searchWrapper.style.display = "none";
    if (searchInput) searchInput.value = "";
    
    const threadId = select.value;
    if (!threadId) {
        wrapper.style.display = "none";
        emptyMsg.style.display = "none";
        return;
    }
    
    loading.style.display = "block";
    wrapper.style.display = "none";
    emptyMsg.style.display = "none";
    tbody.innerHTML = "";
    
    try {
        const response = await fetch(`/admin/spam_report/${threadId}`);
        const data = await response.json();
        loading.style.display = "none";
        
        if (data.success && data.report && data.report.length > 0) {
            data.report.forEach(row => {
                const score = parseFloat(row.average_spam_score || 0).toFixed(1);
                
                // Determine badge style based on spam score
                let scoreBadge = '';
                if (score <= 30) {
                    scoreBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; padding: 4px 10px; border-radius: 8px;">${score} (Temiz)</span>`;
                } else if (score <= 65) {
                    scoreBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; padding: 4px 10px; border-radius: 8px;">${score} (Şüpheli)</span>`;
                } else {
                    scoreBadge = `<span class="badge" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; padding: 4px 10px; border-radius: 8px;">${score} (Yüksek Spam)</span>`;
                }
                
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td data-label="Kullanıcı Adı" style="text-align: left;">
                        <a href="javascript:void(0)" onclick="showUserSpamDetails('${row.username}')">
                            <i class="fas fa-user-circle"></i> @${row.username}
                        </a>
                    </td>
                    <td data-label="Toplam Yorum" style="text-align: center;">${row.total_comments}</td>
                    <td data-label="Format İhlali" style="text-align: center; color: ${row.format_errors > 0 ? '#f87171' : 'rgba(255,255,255,0.7)'};">${row.format_errors}</td>
                    <td data-label="Ort. Spam Puanı" style="text-align: center;">${scoreBadge}</td>
                `;
                tbody.appendChild(tr);
            });
            wrapper.style.display = "block";
            if (searchWrapper) searchWrapper.style.display = "block";
        } else {
            emptyMsg.style.display = "block";
        }
    } catch (e) {
        loading.style.display = "none";
        showAlert("Rapor yüklenemedi: " + e.message, "error");
    }
}
window.loadGroupSpamReport = loadGroupSpamReport;

function filterSpamReportTable(query) {
    const val = query.toLowerCase().trim();
    const rows = document.querySelectorAll("#spamReportTableBody tr");
    rows.forEach(row => {
        const userLink = row.querySelector("td[data-label='Kullanıcı Adı'] a");
        if (userLink) {
            const username = userLink.textContent.toLowerCase().replace("@", "").trim();
            if (username.includes(val)) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        }
    });
}
window.filterSpamReportTable = filterSpamReportTable;

async function showUserSpamDetails(username) {
    const select = document.getElementById("spamReportGroupSelect");
    const modal = document.getElementById("userSpamDetailsModal");
    const titleUser = document.getElementById("spamModalUsername");
    const commentsList = document.getElementById("spamModalCommentsList");
    
    if (!select || !modal || !titleUser || !commentsList) return;
    
    const threadId = select.value;
    titleUser.textContent = username;
    commentsList.innerHTML = `<div style="text-align: center; padding: 20px; color: #aaa;"><i class="fas fa-spinner fa-spin"></i> Yorumlar yükleniyor...</div>`;
    modal.classList.add("show");
    
    try {
        const response = await fetch(`/admin/user_comments/${threadId}/${username}`);
        const data = await response.json();
        
        if (data.success && data.comments && data.comments.length > 0) {
            commentsList.innerHTML = "";
            data.comments.forEach(c => {
                const isFormatValid = c.is_format_valid === 1;
                const formatBadge = isFormatValid 
                    ? `<span class="badge" style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; font-size: 11px; padding: 2px 6px; border-radius: 6px;">Kural Geçti</span>`
                    : `<span class="badge" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; font-size: 11px; padding: 2px 6px; border-radius: 6px;">Kural İhlali</span>`;
                
                const score = parseFloat(c.spam_score || 0).toFixed(1);
                let scoreText = '';
                if (score <= 30) scoreText = `<span style="color: #34d399; font-weight:600;">${score}</span>`;
                else if (score <= 65) scoreText = `<span style="color: #fbbf24; font-weight:600;">${score}</span>`;
                else scoreText = `<span style="color: #f87171; font-weight:600;">${score}</span>`;

                const commentCard = document.createElement("div");
                commentCard.style.background = "rgba(255, 255, 255, 0.02)";
                commentCard.style.border = "1px solid rgba(255, 255, 255, 0.05)";
                commentCard.style.borderRadius = "12px";
                commentCard.style.padding = "14px";
                commentCard.style.marginBottom = "12px";
                
                commentCard.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 12px; color: #aaa;">
                        <div>
                            <i class="fas fa-link me-1"></i> <a href="https://instagram.com/p/${c.post_code}" target="_blank" style="color: var(--accent-primary); text-decoration: none; font-weight: 600;">Post: ${c.post_code}</a>
                        </div>
                        <div>
                            <i class="fas fa-calendar-alt me-1"></i> ${c.created_at}
                        </div>
                    </div>
                    <div style="color: #fff; font-size: 13px; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 8px; margin-bottom: 10px; word-break: break-word; font-style: italic;">
                        "${escapeHtml(c.comment_text)}"
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px;">
                        <div>${formatBadge}</div>
                        <div style="color: rgba(255,255,255,0.8);">Spam Puanı: ${scoreText} / 100</div>
                    </div>
                `;
                commentsList.appendChild(commentCard);
            });
        } else {
            commentsList.innerHTML = `<div style="text-align: center; padding: 20px; color: #aaa;">Yorum detay verisi bulunamadı.</div>`;
        }
    } catch (e) {
        commentsList.innerHTML = `<div style="text-align: center; padding: 20px; color: #f87171;"><i class="fas fa-exclamation-triangle"></i> Yorumlar yüklenemedi: ${e.message}</div>`;
    }
}
window.showUserSpamDetails = showUserSpamDetails;

function closeUserSpamModal() {
    const modal = document.getElementById("userSpamDetailsModal");
    if (modal) modal.classList.remove("show");
}
window.closeUserSpamModal = closeUserSpamModal;

async function showAuditPostDetails(postLink) {
    const modal = document.getElementById("auditPostDetailsModal");
    const loading = document.getElementById("auditPostDetailsLoading");
    const content = document.getElementById("auditPostDetailsContent");
    
    if (!modal || !loading || !content) return;
    
    // Show modal in loading state
    loading.style.display = "block";
    content.style.display = "none";
    modal.classList.add("show");
    
    try {
        const response = await fetch(`/admin/get_post_details?post_link=${encodeURIComponent(postLink)}`);
        const data = await response.json();
        
        if (data.success && data.details) {
            const details = data.details;
            document.getElementById("auditModalPostOwner").textContent = details.sender ? "@" + details.sender : "Bilinmiyor";
            document.getElementById("auditModalPostOwnerFullname").textContent = details.owner_fullname ? details.owner_fullname : "İsim Bilgisi Yok";
            document.getElementById("auditModalPostLikes").textContent = details.like_count ? Number(details.like_count).toLocaleString("tr-TR") : "-";
            document.getElementById("auditModalPostComments").textContent = Number(details.comment_count || 0).toLocaleString("tr-TR");
            document.getElementById("auditModalPostCaption").textContent = details.caption ? details.caption : "Açıklama bulunmuyor.";
            document.getElementById("auditModalPostLinkBtn").href = postLink;
            
            loading.style.display = "none";
            content.style.display = "block";
        } else {
            showAlert(data.message || "Gönderi detayları alınamadı.", "error");
            closeAuditPostDetailsModal();
        }
    } catch (e) {
        console.error("Audit post details error:", e);
        showAlert("Bağlantı hatası oluştu.", "error");
        closeAuditPostDetailsModal();
    }
}


function closeAuditPostDetailsModal() {
    const modal = document.getElementById("auditPostDetailsModal");
    if (modal) {
        modal.classList.remove("show");
    }
}

window.showAuditPostDetails = showAuditPostDetails;
window.closeAuditPostDetailsModal = closeAuditPostDetailsModal;



