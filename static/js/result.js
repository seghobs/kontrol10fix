let notificationTimeout;
let pendingUsername = null;
let pendingButton = null;
let pendingPostLink = null;

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

function updateEksiklerCount(index) {
    const list = document.getElementById(`eksiklerListesi-${index}`);
    const badge = document.getElementById(`elemanSayisi-${index}`);
    if (!list || !badge) return;
    const items = Array.from(list.getElementsByTagName("li"));
    const visibleCount = items.filter((item) => item.style.display !== "none").length;
    badge.innerText = `Eksik: ${visibleCount}`;
}

function showNotification(message) {
    const notification = document.getElementById("notification");
    document.getElementById("notification-message").innerText = message;

    if (notification.classList.contains("visible")) {
        clearTimeout(notificationTimeout);
        notification.classList.remove("visible");
    }

    notification.style.display = "block";
    setTimeout(() => {
        notification.classList.add("visible");
    }, 10);

    notificationTimeout = setTimeout(() => {
        notification.classList.remove("visible");
    }, 3000);
}

function closeModal() {
    document.getElementById("confirmModal").classList.remove("show");
    pendingUsername = null;
    pendingButton = null;
    pendingPostLink = null;
}

function addExemption(username, postLink, button) {
    pendingUsername = username;
    pendingButton = button;
    pendingPostLink = postLink;
    document.getElementById("modalUsername").textContent = `@${username}`;
    document.getElementById("confirmModal").classList.add("show");
}

function confirmExemption() {
    if (!pendingUsername || !pendingButton || !pendingPostLink) {
        return;
    }

    const username = pendingUsername;
    const button = pendingButton;
    const postLink = pendingPostLink;
    closeModal();

    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Kaydediliyor...';

    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    fetch("/add_exemption", {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ post_link: postLink, username }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                const listItem = button.closest("li");
                const parentList = listItem && listItem.parentElement;
                const listId = parentList && parentList.id;
                const indexPart = listId ? listId.split("-").pop() : null;
                const idx = indexPart ? parseInt(indexPart, 10) : null;

                listItem.style.transition = "all 0.3s ease";
                listItem.style.opacity = "0";
                listItem.style.transform = "translateX(20px)";

                setTimeout(() => {
                    listItem.remove();
                    if (idx) updateEksiklerCount(idx);
                    showNotification(`@${username} izinli listesine eklendi!`);
                }, 300);
                return;
            }

            showNotification(`Hata: ${data.message}`);
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-check me-1"></i>Izinli Say';
        })
        .catch(() => {
            showNotification("Bir hata olustu!");
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-check me-1"></i>Izinli Say';
        });
}

function fallbackCopyToClipboard(text, count) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    textArea.style.top = "0";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand("copy");
        showNotification(successful ? `Liste kopyalandi! Toplam eksik sayisi: ${count}` : "Kopyalama basarisiz oldu!");
    } catch (_error) {
        showNotification("Kopyalama desteklenmiyor!");
    }

    document.body.removeChild(textArea);
}

function kopyalaListeyiFrom(listElementId, label) {
    const list = document.getElementById(listElementId);
    if (!list) return;
    const listItems = list.getElementsByTagName("li");
    let text = "";

    for (let i = 0; i < listItems.length; i += 1) {
        const username = listItems[i].getAttribute("data-username");
        if (username) {
            text += `@${username}`;
            if (i < listItems.length - 1) {
                text += "\n";
            }
        }
    }

    const count = listItems.length;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text)
            .then(() => showNotification(`Liste kopyalandi! Toplam ${label} sayisi: ${count}`))
            .catch(() => fallbackCopyToClipboard(text, count));
        return;
    }

    fallbackCopyToClipboard(text, count);
}

function copyEksiklerList(index) {
    kopyalaListeyiFrom(`eksiklerListesi-${index}`, "eksik");
}

function copyCompletedList() {
    kopyalaListeyiFrom("completedList", "tamamlamis kullanici");
}

function filterEksiklerList(index) {
    const list = document.getElementById(`eksiklerListesi-${index}`);
    if (!list) return;
    
    const card = list.closest('.link-card');
    if (!card) return;
    
    const inputEl = card.querySelector(".search-input");
    const input = inputEl ? inputEl.value.toLowerCase() : "";
    const listItems = list.getElementsByTagName("li");

    for (let i = 0; i < listItems.length; i += 1) {

        const item = listItems[i];
        const textValue = item.innerText.toLowerCase();
        item.style.display = textValue.includes(input) ? "" : "none";
    }

    updateEksiklerCount(index);
}

function filterCompletedList() {
    const input = document.getElementById("completedSearchInput").value.toLowerCase();
    const list = document.getElementById("completedList");
    if (!list) return;
    const listItems = list.getElementsByTagName("li");

    for (let i = 0; i < listItems.length; i += 1) {
        const item = listItems[i];
        const textValue = item.innerText.toLowerCase();
        item.style.display = textValue.includes(input) ? "" : "none";
    }
}

window.addExemption = addExemption;
window.closeModal = closeModal;
window.confirmExemption = confirmExemption;
window.copyEksiklerList = copyEksiklerList;
window.copyCompletedList = copyCompletedList;
window.filterEksiklerList = filterEksiklerList;
window.filterCompletedList = filterCompletedList;
window.toggleCompletedSection = toggleCompletedSection;
window.toggleEksiklerSection = toggleEksiklerSection;
window.toggleDetayliRapor = toggleDetayliRapor;
window.toggleUserMissingPosts = toggleUserMissingPosts;
window.copyLink = copyLink;
window.refreshResults = refreshResults;
window.copyUserMissingPosts = copyUserMissingPosts;
window.copyToClipboard = copyToClipboard;

function toggleCompletedSection() {
    const section = document.getElementById("completedSection");
    const icon = document.getElementById("completedSectionIcon");
    if (!section || !icon) return;
    const isCollapsed = section.classList.contains("collapsed");
    if (isCollapsed) {
        slideDown(section);
        icon.style.transform = "rotate(180deg)";
    } else {
        slideUp(section);
        icon.style.transform = "rotate(0deg)";
    }
}

function toggleEksiklerSection(index) {
    const section = document.getElementById(`eksiklerSection-${index}`);
    const icon = document.getElementById(`eksiklerIcon-${index}`);
    if (!section || !icon) return;
    const isCollapsed = section.classList.contains("collapsed");
    if (isCollapsed) {
        slideDown(section);
        icon.style.transform = "rotate(180deg)";
    } else {
        slideUp(section);
        icon.style.transform = "rotate(0deg)";
    }
}

function toggleDetayliRapor() {
    const body = document.getElementById("detayliRaporContent");
    const icon = document.getElementById("detayliRaporIcon");
    if (!body || !icon) return;
    const isCollapsed = body.classList.contains("collapsed");
    if (isCollapsed) {
        slideDown(body);
        icon.style.transform = "rotate(180deg)";
    } else {
        slideUp(body);
        icon.style.transform = "rotate(0deg)";
    }
}

function toggleUserMissingPosts(username, idx) {
    const body = document.getElementById("missing-posts-" + username);
    const icon = document.getElementById("user-icon-" + idx);
    if (!body || !icon) return;
    const isCollapsed = body.classList.contains("collapsed");
    if (isCollapsed) {
        slideDown(body);
        icon.style.transform = "rotate(180deg)";
    } else {
        slideUp(body);
        icon.style.transform = "rotate(0deg)";
    }
}

function copyLink(link) {
    navigator.clipboard.writeText(link).then(() => {
        showNotification("Link kopyalandi!");
    }).catch(() => {
        showNotification("Link kopyalanamadi!");
    });
}

function copyUserMissingPosts(username) {
    const container = document.getElementById('missing-posts-' + username);
    if (!container) return;
    
    const links = [];
    container.querySelectorAll('a').forEach(a => {
        links.push(a.textContent);
    });
    
    const text = links.join('\n');
    navigator.clipboard.writeText(text).then(() => {
        showNotification("@" + username + " için " + links.length + " link kopyalandı!");
    }).catch(() => {
        showNotification("Kopyalama başarısız!");
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification("Kopyalandı!");
    }).catch(() => {
        showNotification("Kopyalama başarısız!");
    });
}

function refreshResults() {
    const links = [];
    document.querySelectorAll('.eksikler-list').forEach(list => {
        const postLink = list.dataset.postLink;
        if (postLink && !links.includes(postLink)) {
            links.push(postLink);
        }
    });
    
    const groupUsers = [];
    document.querySelectorAll('.eksikler-list li').forEach(item => {
        const username = item.dataset.username;
        if (username && !groupUsers.includes(username)) {
            groupUsers.push(username);
        }
    });
    
    const allCommented = [];
    document.querySelectorAll('#completedList li').forEach(item => {
        const username = item.dataset.username;
        if (username) {
            allCommented.push(username);
        }
    });
    
    const allUsers = [...groupUsers, ...allCommented];
    
    if (links.length > 0) {
        const linkParam = encodeURIComponent(links.join('\n'));
        const groupParam = encodeURIComponent(allUsers.join(' '));
        window.location.href = `/?refresh=1&link=${linkParam}&group=${groupParam}`;
    }
}

function showCommentModal(username) {
    const comments = (window.userComments && window.userComments[username.toLowerCase()]) || [];
    const usernameSpan = document.getElementById("commentModalUsername");
    const contentBlock = document.getElementById("commentModalContent");
    const warningBlock = document.getElementById("commentModalWarning");
    
    if (usernameSpan) usernameSpan.textContent = username;
    
    const isViolating = window.invalidCommentUsers && window.invalidCommentUsers.includes(username.toLowerCase());
    if (warningBlock) {
        warningBlock.style.display = isViolating ? "block" : "none";
    }
    
    if (contentBlock) {
        if (comments.length === 0) {
            contentBlock.textContent = "(Yorum içeriği bulunamadı)";
        } else if (comments.length === 1) {
            contentBlock.textContent = comments[0];
        } else {
            contentBlock.innerHTML = comments.map((c, idx) => `<div style="margin-bottom: ${idx === comments.length - 1 ? '0' : '10px'};">${idx + 1}. ${c}</div>`).join('');
        }
    }
    
    const modal = document.getElementById("commentDetailModal");
    if (modal) {
        modal.classList.add("show");
    }
}

function closeCommentModal() {
    const modal = document.getElementById("commentDetailModal");
    if (modal) {
        modal.classList.remove("show");
    }
}

window.showCommentModal = showCommentModal;
window.closeCommentModal = closeCommentModal;

window.onload = function onLoad() {
    const lists = document.querySelectorAll(".eksikler-list");
    lists.forEach((list, idx) => {
        const indexPart = list.id.split("-").pop();
        const index = parseInt(indexPart, 10);
        if (index) updateEksiklerCount(index);
    });
    
    const completedList = document.getElementById("completedList");
    if (completedList) {
        completedList.addEventListener("click", (e) => {
            // Sürükleme kulbu (drag-handle) tıklandıysa modalı açma
            if (e.target.closest(".drag-handle-inner")) {
                return;
            }
            const li = e.target.closest("li.list-group-item");
            if (li) {
                const username = li.getAttribute("data-username");
                if (username) {
                    showCommentModal(username);
                }
            }
        });
        
        const items = completedList.querySelectorAll("li.list-group-item");
        items.forEach(item => {
            item.style.cursor = "pointer";
            item.title = "Kullanıcının yazdığı yorumu görmek için tıklayın";
        });
    }
    
    window.addEventListener("click", (e) => {
        const modal = document.getElementById("commentDetailModal");
        if (e.target === modal) {
            closeCommentModal();
        }
    });

    // Anlık Paylaşım Değiştirici
    if (window.resultThreadId) {
        const dropdownTextEl = document.getElementById("resultPostDropdownText");
        const optionsEl = document.getElementById("resultPostDropdownOptions");
        const containerEl = document.getElementById("resultPostSelectorContainer");
        
        if (dropdownTextEl && optionsEl && containerEl) {
            // Dün ve bugün atılan postları paralel çekelim
            Promise.all([
                fetch(`/api/get_group_posts/${window.resultThreadId}?date=yesterday`).then(r => r.json()),
                fetch(`/api/get_group_posts/${window.resultThreadId}?date=today`).then(r => r.json())
            ])
            .then(([resYest, resToday]) => {
                const postsYest = (resYest && resYest.posts) || [];
                const postsToday = (resToday && resToday.posts) || [];
                
                // Tekilleştirme
                const allPostsMap = new Map();
                postsToday.forEach(p => allPostsMap.set(p.url, p));
                postsYest.forEach(p => allPostsMap.set(p.url, p));
                
                const combinedPosts = Array.from(allPostsMap.values());
                
                if (combinedPosts.length > 0) {
                    optionsEl.innerHTML = "";
                    
                    combinedPosts.forEach(p => {
                        const div = document.createElement("div");
                        div.className = "dropdown-option";
                        
                        const labelText = `@${p.username || 'Bilinmiyor'} (${p.date || 'Tarih Yok'})`;
                        div.textContent = labelText;
                        div.setAttribute("data-value", p.url);
                        
                        const cleanPUrl = p.url ? p.url.trim().replace(/\/$/, "") : "";
                        const cleanCheckedUrl = window.checkedPostUrl ? window.checkedPostUrl.trim().replace(/\/$/, "") : "";
                        
                        if (cleanPUrl === cleanCheckedUrl) {
                            div.classList.add("selected");
                            dropdownTextEl.textContent = labelText;
                        }
                        
                        div.addEventListener("click", () => {
                            optionsEl.querySelectorAll(".dropdown-option").forEach(o => o.classList.remove("selected"));
                            div.classList.add("selected");
                            dropdownTextEl.textContent = labelText;
                            toggleResultDropdown('resultPostDropdown'); // close menu
                            changeCheckedPost(p.url);
                        });
                        
                        optionsEl.appendChild(div);
                    });
                    
                    containerEl.style.display = "block";
                    const btnWrapper = document.getElementById("togglePostSelectorBtnWrapper");
                    if (btnWrapper) btnWrapper.style.display = "block";
                } else {
                    containerEl.style.display = "none";
                }
            })
            .catch(err => {
                console.error("Grup paylaşımlarını yükleme hatası:", err);
                containerEl.style.display = "none";
            });
        }
    }
};

function toggleResultDropdown(id) {
    const dropdown = document.getElementById(id);
    if (!dropdown) return;
    const trigger = dropdown.querySelector('.dropdown-trigger');
    const menu = dropdown.querySelector('.dropdown-menu');
    if (!trigger || !menu) return;
    
    // Diğer açık dropdownları kapat
    document.querySelectorAll('.dropdown-menu').forEach(m => {
        if (m !== menu) m.classList.remove('show');
    });
    document.querySelectorAll('.dropdown-trigger').forEach(t => {
        if (t !== trigger) t.classList.remove('active');
    });
    
    trigger.classList.toggle('active');
    menu.classList.toggle('show');
}

function filterResultDropdown(dropdownId, value) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    const options = dropdown.querySelectorAll(".dropdown-option");
    const query = value.toLowerCase();
    
    options.forEach(opt => {
        const text = opt.textContent.toLowerCase();
        opt.style.display = text.includes(query) ? "" : "none";
    });
}

// Click outside helper
window.addEventListener("click", (e) => {
    if (!e.target.closest('.custom-dropdown')) {
        document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
        document.querySelectorAll('.dropdown-trigger').forEach(t => t.classList.remove('active'));
    }
});

function togglePostSelectorCard() {
    const container = document.getElementById("resultPostSelectorContainer");
    if (!container) return;
    const isCollapsed = container.classList.contains("collapsed");
    if (isCollapsed) {
        slideDown(container);
    } else {
        slideUp(container);
    }
}

window.toggleResultDropdown = toggleResultDropdown;
window.filterResultDropdown = filterResultDropdown;
window.togglePostSelectorCard = togglePostSelectorCard;

function changeCheckedPost(newUrl) {
    const todayStr = getIstanbulDateStr();
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    fetch("/api/save_selected_post", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({
            thread_id: window.resultThreadId,
            date: todayStr,
            post_url: newUrl
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // İlerleme overlay'ini göster
            const overlay = document.getElementById("progressOverlay");
            if (overlay) {
                overlay.style.display = "flex";
                void overlay.offsetHeight;
                overlay.classList.add("show");
            }
            
            // Gizli formu doldur ve gönder
            const refreshPostLink = document.getElementById("refreshPostLink");
            if (refreshPostLink) {
                refreshPostLink.value = newUrl;
            }
            
            const form = document.getElementById("resultRefreshForm");
            if (form) {
                form.submit();
            }
        } else {
            alert("Paylaşım seçimi kaydedilemedi.");
        }
    })
    .catch(err => {
        console.error("Paylaşım değiştirme hatası:", err);
        alert("Bağlantı hatası oluştu.");
    });
}

function getIstanbulDateStr() {
    const d = new Date();
    const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Europe/Istanbul',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
    return formatter.format(d);
}

function showPostDetailsModal(index) {
    const data = window.postDetailsData ? window.postDetailsData[index] : null;
    if (!data) return;
    
    const ownerEl = document.getElementById("modalPostOwner");
    const fullnameEl = document.getElementById("modalPostOwnerFullname");
    const likesEl = document.getElementById("modalPostLikes");
    const commentsEl = document.getElementById("modalPostComments");
    const captionEl = document.getElementById("modalPostCaption");
    const linkBtn = document.getElementById("modalPostLinkBtn");
    
    if (ownerEl) ownerEl.textContent = data.sender ? "@" + data.sender : "Bilinmiyor";
    if (fullnameEl) fullnameEl.textContent = data.owner_fullname ? data.owner_fullname : "İsim Bilgisi Yok";
    if (likesEl) likesEl.textContent = Number(data.like_count).toLocaleString("tr-TR");
    if (commentsEl) commentsEl.textContent = Number(data.comment_count).toLocaleString("tr-TR");
    if (captionEl) captionEl.textContent = data.caption ? data.caption : "Açıklama bulunmuyor.";
    if (linkBtn) linkBtn.href = data.link;
    
    const modal = document.getElementById("postDetailsModal");
    if (modal) {
        modal.classList.add("show");
    }
}

function closePostDetailsModal() {
    const modal = document.getElementById("postDetailsModal");
    if (modal) {
        modal.classList.remove("show");
    }
}

window.showPostDetailsModal = showPostDetailsModal;
window.closePostDetailsModal = closePostDetailsModal;
