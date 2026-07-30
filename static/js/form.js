function showTokenErrorModal(message) {
    showValidationToast(message);
}
// Global variables for Tag System
let editingUserIndex = -1;


function renderUserTags() {
    const textarea = document.getElementById("grup_uye");
    const container = document.getElementById("userTagContainer");
    const searchWrapper = document.getElementById("tagSearchWrapper");
    const searchInput = document.getElementById("tagSearchInput");
    
    if (!textarea || !container) return;

    const users = textarea.value.split("\n").filter((user) => user.trim() !== "");
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : "";

    // Show/Hide search box based on list presence
    if (searchWrapper) {
        searchWrapper.style.display = users.length > 0 ? "block" : "none";
    }

    container.innerHTML = "";

    users.forEach((user, index) => {
        // If searching, skip if no match
        if (searchTerm && !user.toLowerCase().includes(searchTerm)) {
            return;
        }

        const tag = document.createElement("div");
        tag.className = "user-tag";
        tag.innerHTML = `
            <i class="fas fa-user-circle"></i>
            <span>${user}</span>
            <i class="fas fa-times remove-tag" onclick="removeUserTag(event, ${index})"></i>
        `;
        tag.onclick = (e) => {
            if (!e.target.classList.contains('remove-tag')) {
                openEditModal(user, index);
            }
        };
        container.appendChild(tag);
    });

    const userCountDisplay = document.getElementById("user_count");
    if (userCountDisplay) {
        userCountDisplay.textContent = users.length + " Adet kullanıcı eklendi.";
    }
}

function filterUserTags(val) {
    renderUserTags();
}

window.filterUserTags = filterUserTags;


function removeUserTag(event, index) {
    event.stopPropagation();
    const textarea = document.getElementById("grup_uye");
    let users = textarea.value.split("\n").filter((user) => user.trim() !== "");
    users.splice(index, 1);
    textarea.value = users.join("\n");
    renderUserTags();
}

function openEditModal(username, index) {
    editingUserIndex = index;
    const modal = document.getElementById("editUserModal");
    const input = document.getElementById("editUserInput");
    if (modal && input) {
        input.value = username;
        modal.classList.add("show");
        input.focus();
    }
}

function closeEditModal() {
    const modal = document.getElementById("editUserModal");
    if (modal) modal.classList.remove("show");
    editingUserIndex = -1;
}

function saveEditedUser() {
    const input = document.getElementById("editUserInput");
    const textarea = document.getElementById("grup_uye");
    if (!input || !textarea || editingUserIndex === -1) return;

    const newName = input.value.trim();
    if (newName) {
        let users = textarea.value.split("\n").filter((user) => user.trim() !== "");
        users[editingUserIndex] = newName;
        textarea.value = users.join("\n");
        renderUserTags();
        closeEditModal();
    }
}

function addUserFromInput() {
    const input = document.getElementById("tagAddInput");
    const textarea = document.getElementById("grup_uye");
    if (!input || !textarea) return;

    const username = input.value.trim();
    if (username) {
        const currentVal = textarea.value.trim();
        textarea.value = currentVal ? currentVal + "\n" + username : username;
        input.value = "";
        renderUserTags();
    }
}

function updateUserCount() {
    renderUserTags();
}

window.removeUserTag = removeUserTag;
window.closeEditModal = closeEditModal;
window.saveEditedUser = saveEditedUser;
window.updateUserCount = updateUserCount;


// Global değişken - seçili grup ID'si
let currentThreadId = '';

function getFavorites() {
    const favs = localStorage.getItem('fav_groups');
    return favs ? JSON.parse(favs) : [];
}

function toggleFavorite(e, threadId) {
    e.stopPropagation();
    let favs = getFavorites();
    const index = favs.indexOf(threadId);
    
    if (index > -1) {
        favs.splice(index, 1);
    } else {
        favs.push(threadId);
    }
    
    localStorage.setItem('fav_groups', JSON.stringify(favs));
    
    // UI'ı yeniden yükle (sıralama için)
    loadGroups();
}

function loadGroups() {
    const select = document.getElementById("groupSelect");
    const dropdownText = document.querySelector('#groupDropdown .dropdown-text');
    const dropdownOptions = document.querySelector('#groupDropdown .dropdown-options');
    
    dropdownOptions.innerHTML = '<div class="dropdown-option" style="color: rgba(255,255,255,0.5);">Gruplar yükleniyor...</div>';
    
    fetch("/api/get_groups")
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                dropdownOptions.innerHTML = '<div class="dropdown-option" style="color: rgba(255,255,255,0.5);">Grup bulunamadı</div>';
                showTokenErrorModal(data.error || "Gruplar yüklenemedi");
                return;
            }
            
            if (data.groups && data.groups.length > 0) {
                dropdownOptions.innerHTML = '';
                
                // Favorilere göre sırala
                const favs = getFavorites();
                const sortedGroups = [...data.groups].sort((a, b) => {
                    const aFav = favs.includes(a.id);
                    const bFav = favs.includes(b.id);
                    if (aFav && !bFav) return -1;
                    if (!aFav && bFav) return 1;
                    return 0;
                });

                sortedGroups.forEach(g => {
                    const isFav = favs.includes(g.id);
                    const div = document.createElement('div');
                    div.className = 'dropdown-option';
                    div.innerHTML = `
                        <i class="fas fa-users" style="color: var(--accent-caramel);"></i> 
                        <span style="flex-grow: 1;">${g.name} <span style="opacity: 0.6; font-size: 11px;">(${g.member_count})</span></span>
                        <i class="fas fa-star fav-btn ${isFav ? 'active' : ''}" onclick="toggleFavorite(event, '${g.id}')"></i>
                    `;
                    div.onclick = function(e) {
                        e.stopPropagation();
                        const textSpan = document.querySelector('#groupDropdown .dropdown-text');
                        textSpan.textContent = `${g.name} (${g.member_count} üye)`;
                        
                        // Set value to hidden select and global variable
                        const hiddenSelect = document.getElementById('groupSelect');
                        if (hiddenSelect) {
                            hiddenSelect.value = g.id;
                        }
                        currentThreadId = g.id;
                        window.currentGroupMemberCount = g.member_count;
                        const threadIdInput = document.getElementById('thread_id_input');
                        if (threadIdInput) {
                            threadIdInput.value = g.id;
                        }
                        
                        // Form hafif blur animasyonu (1 saniye)
                        const containerElement = document.querySelector('.container');
                        if (containerElement) {
                            containerElement.style.transition = 'filter 0.4s ease, opacity 0.4s ease';
                            containerElement.style.filter = 'blur(4px)';
                            containerElement.style.opacity = '0.85';
                            
                            setTimeout(() => {
                                containerElement.style.filter = 'blur(0)';
                                containerElement.style.opacity = '1';
                                setTimeout(() => {
                                    containerElement.style.transition = '';
                                }, 400);
                            }, 1000); // 1 saniye sonra açılacak
                        }
                        
                        // Load members when group is selected - pass threadId directly
                        loadGroupMembers(g.id);
                        
                        // Update the badge
                        const badge = document.getElementById('selectedGroupBadge');
                        if (badge) {
                            badge.textContent = g.name;
                            badge.style.display = 'inline-block';
                        }
                        
                        // Close dropdown
                        document.querySelector('#groupDropdown .dropdown-menu').classList.remove('show');
                        document.querySelector('#groupDropdown .dropdown-trigger').classList.remove('active');
                    };
                    dropdownOptions.appendChild(div);
                });
            } else {
                dropdownOptions.innerHTML = '<div class="dropdown-option" style="color: rgba(255,255,255,0.5);">Grup bulunamadı</div>';
            }
        })
        .catch(err => {
            dropdownOptions.innerHTML = '<div class="dropdown-option" style="color: rgba(255,255,255,0.5);">Hata oluştu</div>';
            showTokenErrorModal("Gruplar yüklenemedi: " + err.message);
        });
}

function loadGroupMembers(threadIdFromDropdown) {
    // Get threadId either from parameter or from hidden select
    let threadId = threadIdFromDropdown;
    if (!threadId) {
        const select = document.getElementById("groupSelect");
        threadId = select ? select.value : '';
    }
    
    const textarea = document.getElementById("grup_uye");
    const postsSection = document.getElementById("groupPostsSection");
    const postSelect = document.getElementById("postSelect");
    const dropdownText = document.querySelector('#groupDropdown .dropdown-text');
    
    if (!threadId) {
        postsSection.style.display = "none";
        const filterWrapper = document.getElementById("sharersFilterWrapper");
        if (filterWrapper) filterWrapper.style.display = "none";
        const likesFilterWrapper = document.getElementById("lowLikesFilterWrapper");
        if (likesFilterWrapper) likesFilterWrapper.style.display = "none";
        return;
    }
    
    toggleGroupLoading(true);

    if (dropdownText && threadId) {
        // Keep the current text (group name) but add a loading suffix
        const currentName = dropdownText.textContent;
        if (!currentName.includes("yükleniyor")) {
            dropdownText.textContent = `${currentName} (Yükleniyor...)`;
        }
    }

    
    const hiddenSelect = document.getElementById("groupSelect");
    if (hiddenSelect) {
        hiddenSelect.disabled = true;
    }
    
    fetch("/api/get_group_members/" + threadId)
        .then(r => r.json())
        .then(data => {
            if (hiddenSelect) {
                hiddenSelect.disabled = false;
            }
            
            if (!data.ok) {
                showTokenErrorModal(data.error || "Üyeler yüklenemedi");
                if (dropdownText) dropdownText.textContent = "-- Instagram Grubu Seç --";
                return;
            }
            

            if (dropdownText) {
                dropdownText.textContent = dropdownText.textContent.replace(" (Yükleniyor...)", "");
            }

            if (data.usernames && data.usernames.length > 0) {

                window.fullGroupMembers = data.usernames;
                const isChecked = document.getElementById("onlySharersCheck")?.checked;
                if (!isChecked) {
                    textarea.value = data.usernames.join("\n");
                    updateUserCount();
                } else {
                    // It will be handled in loadGroupPosts silently
                }
            }
        })
        .catch(err => {
            if (hiddenSelect) {
                hiddenSelect.disabled = false;
            }
            if (dropdownText) dropdownText.textContent = "-- Instagram Grubu Seç --";

            if (dropdownText) {
                dropdownText.textContent = dropdownText.textContent.replace(" (Yükleniyor...)", "");
            }
            showTokenErrorModal("Üyeler yüklenemedi: " + err.message);

        })
        .finally(() => {
            window.isMembersLoading = false;
            checkAndEnableToggles();
        });
    
    // Paylaşımları yükle - threadId ile birlikte
    postsSection.style.display = "block";
    const filterWrapper = document.getElementById("sharersFilterWrapper");
    if (filterWrapper) {
        filterWrapper.style.display = "flex";
        filterWrapper.style.opacity = "0.5";
        filterWrapper.style.pointerEvents = "none";
        const c1 = document.getElementById("onlySharersCheck");
        if(c1) c1.disabled = true;
    }
    const likesFilterWrapper = document.getElementById("lowLikesFilterWrapper");
    if (likesFilterWrapper) {
        likesFilterWrapper.style.display = "flex";
        likesFilterWrapper.style.opacity = "0.5";
        likesFilterWrapper.style.pointerEvents = "none";
        const c2 = document.getElementById("lowLikesCheck");
        if(c2) c2.disabled = true;
    }
    
    window.isMembersLoading = true;
    window.isPostsLoading = true;
    
    loadGroupPosts(threadId);
}

// Wrapper function to load posts when date changes
function selectDateAndLoadPosts(dateValue, dateText) {
    console.log("selectDateAndLoadPosts called:", dateValue, dateText);
    
    // Update hidden select
    const dateFilter = document.getElementById('dateFilter');
    if (dateFilter) {
        dateFilter.value = dateValue;
        console.log("Set dateFilter value to:", dateValue);
    }
    
    // Update dropdown text
    const textSpan = document.querySelector('#dateDropdown .dropdown-text');
    if (textSpan) {
        textSpan.textContent = dateText;
    }
    
    // Close dropdown
    document.querySelector('#dateDropdown .dropdown-menu').classList.remove('show');
    document.querySelector('#dateDropdown .dropdown-trigger').classList.remove('active');
    
    // Load posts with current group
    loadGroupPostsWithCurrentGroup();
}

// Load posts using current group selection
function loadGroupPostsWithCurrentGroup() {
    console.log("loadGroupPostsWithCurrentGroup called, currentThreadId:", currentThreadId);
    if (currentThreadId) {
        loadGroupPosts(currentThreadId);
    } else {
        // Fallback to hidden select
        const groupSelect = document.getElementById("groupSelect");
        const threadId = groupSelect ? groupSelect.value : '';
        if (threadId) {
            loadGroupPosts(threadId);
        }
    }
}

function addPostLink() {
    const postSelect = document.getElementById("postSelect");
    const link = postSelect.value;
    const linkInput = document.getElementById("post_link_single");
    
    if (link) {
        linkInput.value = link;
        validateForm();
        
        const lowLikesChecked = document.getElementById("lowLikesCheck")?.checked;
        const dateFilter = document.getElementById("dateFilter")?.value || "yesterday";
        if (currentThreadId && !lowLikesChecked && (dateFilter === "yesterday" || dateFilter === "today") && window._checkMode === "single") {
            const todayStr = getIstanbulDateStr();
            saveSelectedPostToDb(currentThreadId, todayStr, link);
        }
    }
}

function addAllPosts() {
    const postSelect = document.getElementById("postSelect");
    const multiInput = document.getElementById("post_link_multi");
    const checkForm = document.getElementById("checkForm");
    
    // Önce eski post_sender inputlarını temizle
    const oldInputs = checkForm.querySelectorAll('.post-sender-input');
    oldInputs.forEach(input => input.remove());
    
    const options = postSelect.querySelectorAll("option");
    const urls = [];
    
    options.forEach(opt => {
        if (opt.value && opt.value.startsWith("http")) {
            urls.push(opt.value);
            // Her post için göndericiyi hidden input olarak ekle
            const sender = opt.dataset.sender || '';
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'post_senders';
            input.className = 'post-sender-input';
            input.value = opt.value + '|' + sender;
            checkForm.appendChild(input);
        }
    });
    
    if (urls.length === 0) {
        return;
    }
    
    // Var olanı silip tamamen yeni yüklenen linkleri basıyoruz
    multiInput.value = urls.join("\n");
    validateForm();
}

function loadGroupPosts(threadIdFromMembers) {
    let threadId = threadIdFromMembers;
    if (!threadId) {
        const groupSelect = document.getElementById("groupSelect");
        threadId = groupSelect ? groupSelect.value : '';
    }
    
    const dateFilterEl = document.getElementById("dateFilter");
    const dateFilter = dateFilterEl ? dateFilterEl.value : 'yesterday';
    const postSelect = document.getElementById("postSelect");
    const dropdownText = document.querySelector('#postDropdown .dropdown-text');
    const dropdownOptions = document.querySelector('#postDropdown .dropdown-options');
    
    console.log("loadGroupPosts called, threadId:", threadId, "dateFilter:", dateFilter);
    
    if (!threadId) {
        console.log("No threadId, returning");
        return;
    }
    
    // Yüklenme başladı, butonları deaktif et
    window.isPostsLoading = true;
    const fw = document.getElementById("sharersFilterWrapper");
    if(fw) { fw.style.opacity = "0.5"; fw.style.pointerEvents = "none"; }
    const c1 = document.getElementById("onlySharersCheck");
    if(c1) c1.disabled = true;
    
    const lw = document.getElementById("lowLikesFilterWrapper");
    if(lw) { lw.style.opacity = "0.5"; lw.style.pointerEvents = "none"; }
    const c2 = document.getElementById("lowLikesCheck");
    if(c2) c2.disabled = true;
    
    if (dropdownText) {
        dropdownText.textContent = "Paylaşımlar yükleniyor...";
    }
    
    fetch("/api/get_group_posts/" + threadId + "?date=" + dateFilter)
        .then(r => r.json())
        .then(data => {
            if (dropdownText) {
                dropdownText.textContent = "-- Paylaşım Seç --";
            }
            if (!data.ok) {
                dropdownOptions.innerHTML = '<div class="dropdown-option" style="color: rgba(255,255,255,0.5);">Paylaşım bulunamadı</div>';
                return;
            }
            
            if (data.posts) {
                window.allFetchedPosts = data.posts;
            } else {
                window.allFetchedPosts = [];
            }

            // Dün hiç paylaşım yoksa otomatik Bugün'e geç
            if (window.allFetchedPosts.length === 0 && dateFilter === "yesterday") {
                console.log("Dün atılan paylaşım bulunamadı, otomatik olarak Bugün'e geçiliyor...");
                selectDateAndLoadPosts('today', 'Bugün');
                return;
            }
            
            renderPosts();
            
            // Otomatik paylaşım seçimini tetikle
            handleAutoSelect(threadId);
            
            // Eğer checkbox işaretliyse, paylaşımlar yüklendikten sonra üye listesini otomatik filtrele
            const isChecked = document.getElementById("onlySharersCheck")?.checked;
            if (isChecked) {
                fetchSharers(true); // silent
            }
            
            // Eğer toplu kontrol modundaysa, paylaşımları otomatik ekle
            if (window._checkMode === "multi") {
                addAllPosts();
            }
        })
        .catch(err => {
            if (dropdownText) {
                dropdownText.textContent = "-- Paylaşım Seç --";
            }
            dropdownOptions.innerHTML = '<div class="dropdown-option" style="color: rgba(255,255,255,0.5);">Hata oluştu</div>';
        })
        .finally(() => {
            window.isPostsLoading = false;
            checkAndEnableToggles();
        });
}

function checkAndEnableToggles() {
    if (window.isMembersLoading || window.isPostsLoading) return;
    
    toggleGroupLoading(false);

    const filterWrapper = document.getElementById("sharersFilterWrapper");
    if (filterWrapper) {
        filterWrapper.style.opacity = "1";
        filterWrapper.style.pointerEvents = "auto";
        const c1 = document.getElementById("onlySharersCheck");
        if(c1) c1.disabled = false;
    }
    
    const likesFilterWrapper = document.getElementById("lowLikesFilterWrapper");
    if (likesFilterWrapper) {
        likesFilterWrapper.style.opacity = "1";
        likesFilterWrapper.style.pointerEvents = "auto";
        const c2 = document.getElementById("lowLikesCheck");
        if(c2) c2.disabled = false;
    }
}

function handleLowLikesCheckbox() {
    renderPosts();
}

function renderPosts() {
    const postSelect = document.getElementById("postSelect");
    const dropdownText = document.querySelector('#postDropdown .dropdown-text');
    const dropdownOptions = document.querySelector('#postDropdown .dropdown-options');
    
    if (!postSelect || !dropdownOptions) return;
    
    postSelect.innerHTML = '';
    const lowLikesChecked = document.getElementById("lowLikesCheck")?.checked;
    
    let postsToRender = window.allFetchedPosts || [];
    
    // Eğer '90 altı' filtresi aktifse
    if (lowLikesChecked) {
        postsToRender = postsToRender.filter(p => p.like_count !== undefined && p.like_count !== null && p.like_count <= 90);
    }
    
    if (postsToRender.length > 0) {
        dropdownOptions.innerHTML = '';
        postsToRender.forEach(p => {
            const icon = p.media_type === 'video' ? '🎬' : '📷';
            
            // Add to hidden select
            const opt = document.createElement('option');
            opt.value = p.url;
            opt.dataset.sender = p.username || '';
            opt.text = `${icon} ${p.username} - ${p.date}`;
            postSelect.appendChild(opt);
            
            // Add to custom dropdown
            const div = document.createElement('div');
            div.className = 'dropdown-option';
            // Optional: show likes if lowLikesChecked to confirm
            const likesHtml = lowLikesChecked && p.like_count !== -1 ? ` <span style="color: #ef4444; font-size: 10px; margin-left: 5px;">(❤ ${p.like_count})</span>` : '';
            div.innerHTML = `<span class="icon">${icon}</span> <span>${p.username}</span>${likesHtml} <span style="opacity: 0.6; font-size: 11px;">${p.date}</span>`;
            div.onclick = function() {
                dropdownText.textContent = `${icon} ${p.username} - ${p.date}`;
                postSelect.value = p.url;
                postSelect.dispatchEvent(new Event('change'));
                
                // Form hafif blur animasyonu (1 saniye)
                const containerElement = document.querySelector('.container');
                if (containerElement) {
                    containerElement.style.transition = 'filter 0.4s ease, opacity 0.4s ease';
                    containerElement.style.filter = 'blur(4px)';
                    containerElement.style.opacity = '0.85';
                    
                    setTimeout(() => {
                        containerElement.style.filter = 'blur(0)';
                        containerElement.style.opacity = '1';
                        setTimeout(() => {
                            containerElement.style.transition = '';
                        }, 400);
                    }, 1000); // 1 saniye sonra açılacak
                }
                
                // Close dropdown
                document.querySelector('#postDropdown .dropdown-menu').classList.remove('show');
                document.querySelector('#postDropdown .dropdown-trigger').classList.remove('active');
            };
            dropdownOptions.appendChild(div);
        });
    } else {
        dropdownOptions.innerHTML = '<div class="dropdown-option" style="color: rgba(255,255,255,0.5);">Filtrelenmiş paylaşım bulunamadı</div>';
    }
    
    // Filtreleme sonrası toplu kontroldeysek tekrar ekle
    if (window._checkMode === "multi") {
        addAllPosts();
    }
}

window.addPostLink = addPostLink;
window.loadGroupPosts = loadGroupPosts;
window.loadGroupPostsWithCurrentGroup = loadGroupPostsWithCurrentGroup;
window.selectDateAndLoadPosts = selectDateAndLoadPosts;
window.addAllPosts = addAllPosts;

window.loadGroups = loadGroups;
window.loadGroupMembers = loadGroupMembers;
window.addPostLink = addPostLink;


function setCheckMode(mode) {
    window._checkMode = mode === "multi" ? "multi" : "single";

    const singleBtn = document.getElementById("modeSingle");
    const multiBtn = document.getElementById("modeMulti");
    const hint = document.getElementById("modeHint");
    const singleContent = document.getElementById("singleModeContent");
    const multiContent = document.getElementById("multiModeContent");
    const singleInput = document.getElementById("post_link_single");
    const multiTextarea = document.getElementById("post_link_multi");

    if (!singleBtn || !multiBtn || !hint || !singleContent || !multiContent || !singleInput || !multiTextarea) return;

    if (mode === "multi") {
        singleBtn.classList.remove("active");
        multiBtn.classList.add("active");
        hint.textContent = "Toplu kontrol: Her satira bir post/reel linki yazabilirsiniz.";
        
        // Hide single, Show multi with animation
        singleContent.classList.remove("active");
        setTimeout(() => {
            singleContent.style.display = "none";
            multiContent.style.display = "block";
            setTimeout(() => {
                multiContent.classList.add("active");
                multiTextarea.disabled = false;
                singleInput.disabled = true;
            }, 10);
        }, 300);

        multiTextarea.rows = 4;
        if (!multiTextarea.value.includes("\n")) {
            multiTextarea.placeholder = "Her satira bir post/reel linki yazin\nhttps://www.instagram.com/p/...\nhttps://www.instagram.com/reel/...";
        }
        
        const postDropdown = document.getElementById("postDropdown");
        if (postDropdown) postDropdown.style.display = "none";
        
        // Eğer zaten grup seçilmiş ve paylaşımlar yüklüyse otomatik ekle
        const postSelect = document.getElementById("postSelect");
        if (postSelect) {
            const hasPosts = Array.from(postSelect.options).some(opt => opt.value && opt.value.startsWith("http"));
            if (hasPosts) {
                addAllPosts();
            }
        }
    } else {
        multiBtn.classList.remove("active");
        singleBtn.classList.add("active");
        hint.textContent = "Tekli kontrol: Tek bir post/reel linki gir.";
        
        // Hide multi, Show single with animation
        multiContent.classList.remove("active");
        setTimeout(() => {
            multiContent.style.display = "none";
            singleContent.style.display = "block";
            setTimeout(() => {
                singleContent.classList.add("active");
                singleInput.disabled = false;
                multiTextarea.disabled = true;
            }, 10);
        }, 300);

        singleInput.placeholder = "https://www.instagram.com/p/...";
        

        const postDropdown = document.getElementById("postDropdown");
        if (postDropdown) postDropdown.style.display = "block";
    }
    
    // Update button state for the new mode
    validateForm();
}




function validateForm() {
    const submitBtn = document.getElementById("submitCheckBtn");
    if (!submitBtn) return;

    let isValid = false;
    if (window._checkMode === "multi") {
        const multiInput = document.getElementById("post_link_multi");
        isValid = multiInput && multiInput.value.trim().length > 0;
    } else {
        const singleInput = document.getElementById("post_link_single");
        isValid = singleInput && singleInput.value.trim().length > 0;
    }

    // We don't disable the button anymore to allow clicks for feedback
    if (!isValid) {
        submitBtn.classList.add("btn-disabled");
    } else {
        submitBtn.classList.remove("btn-disabled");
    }
}

function showValidationToast(customMessage) {
    const toast = document.getElementById("validationToast");
    if (toast) {
        const textSpan = toast.querySelector("span");
        if (textSpan) {
            textSpan.textContent = customMessage || "Kontrol yapmak için mutlaka bir paylaşım seçmeniz gerekiyor!";
        }
        toast.classList.add("show");
        setTimeout(() => {
            toast.classList.remove("show");
        }, 3000);
    }
}


window.validateForm = validateForm;

function toggleGroupLoading(show) {

    const overlay = document.getElementById("groupLoadingOverlay");
    if (overlay) {
        overlay.style.display = show ? "flex" : "none";
    }
}

function showProgress(show) {
    const overlay = document.getElementById("progressOverlay");
    if (!overlay) return;
    overlay.style.display = show ? "flex" : "none";
    overlay.classList.toggle("show", show);
}

function setProgressText(text, percent) {
    const el = document.getElementById("progressText");
    const bar = document.getElementById("progressBar");
    if (el) el.textContent = text;
    if (bar) {
        bar.style.width = (percent || 0) + "%";
        bar.setAttribute("aria-valuenow", percent || 0);
    }
}


document.addEventListener("DOMContentLoaded", () => {
    // Initial render for tags
    renderUserTags();

    // Tag System: Add on Enter
    const tagAddInput = document.getElementById("tagAddInput");
    if (tagAddInput) {
        tagAddInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                addUserFromInput();
            }
        });
    }

    // Modal behavior: close on click outside
    window.addEventListener("click", (e) => {
        const editModal = document.getElementById("editUserModal");
        if (e.target === editModal) {
            closeEditModal();
        }
    });


    // Form validation listeners
    const singleInput = document.getElementById("post_link_single");
    const multiInput = document.getElementById("post_link_multi");
    
    if (singleInput) {
        singleInput.addEventListener("input", validateForm);
        singleInput.addEventListener("change", () => {
            const link = singleInput.value.trim();
            const lowLikesChecked = document.getElementById("lowLikesCheck")?.checked;
            const dateFilter = document.getElementById("dateFilter")?.value || "yesterday";
            if (currentThreadId && link && !lowLikesChecked && (dateFilter === "yesterday" || dateFilter === "today") && window._checkMode === "single") {
                const todayStr = getIstanbulDateStr();
                saveSelectedPostToDb(currentThreadId, todayStr, link);
            }
        });
    }
    if (multiInput) multiInput.addEventListener("input", validateForm);

    // Initial validation
    validateForm();


    // Form submission validation
    const checkForm = document.getElementById("checkForm");
    if (checkForm) {
        checkForm.addEventListener("submit", (e) => {
            const multiInput = document.getElementById("post_link_multi");
            const singleInput = document.getElementById("post_link_single");
            
            let isValid = false;
            let customError = null;
            if (window._checkMode === "multi") {
                isValid = multiInput && multiInput.value.trim().length > 0;
            } else {
                isValid = singleInput && singleInput.value.trim().length > 0;
                if (isValid) {
                    const postUrl = singleInput.value.trim();
                    const chosenPost = (window.allFetchedPosts || []).find(p => p.url === postUrl);
                    if (chosenPost) {
                        const isRecent = chosenPost.is_recent === true;
                        if (!isRecent) {
                            isValid = false;
                            customError = "Sadece dün veya bugün yüklenmiş paylaşımların kontrolünü yapabilirsiniz!";
                        }
                    }
                }
            }


            if (!isValid) {
                e.preventDefault();
                showValidationToast(customError);
                
                // Target selection: single mode -> postDropdown, multi mode -> groupDropdown
                const isMulti = window._checkMode === "multi";
                const dropdownId = isMulti ? "groupDropdown" : "postDropdown";
                const dropdown = document.getElementById(dropdownId);
                
                if (dropdown) {
                    dropdown.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    // Add a pulse effect to catch attention
                    dropdown.classList.add("pulse-highlight");
                    setTimeout(() => dropdown.classList.remove("pulse-highlight"), 2000);

                    setTimeout(() => {
                        const menu = dropdown.querySelector('.dropdown-menu');
                        if (menu && !menu.classList.contains('show')) {
                            toggleDropdown(dropdownId);
                        }
                    }, 600);
                }
                return false;
            }


            // If valid, show loading state
            const submitBtn = document.getElementById("submitCheckBtn");
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Kontrol Ediliyor...';
                submitBtn.classList.add("btn-loading-border");
            }
            
            // Kontrol işlemi boyunca ekranı bulanıklaştır (Sunucu yanıt verip sayfa yönlenene kadar kalır)
            const containerElement = document.querySelector('.container');
            if (containerElement) {
                containerElement.style.transition = 'filter 1.5s ease, opacity 1.5s ease';
                containerElement.style.filter = 'blur(15px)';
                containerElement.style.opacity = '0.4';
            }
        });
    }


    const tokenErrorMessage = document.body.dataset.tokenErrorMessage;

    document.getElementById("closeTokenModalBtn").addEventListener("click", () => {
        document.getElementById("tokenErrorModal").classList.remove("show");
    });

    document.getElementById("tokenErrorModal").addEventListener("click", (event) => {
        if (event.target.id === "tokenErrorModal") {
            event.currentTarget.classList.remove("show");
        }
    });

    if (tokenErrorMessage) {
        showTokenErrorModal(tokenErrorMessage);
    }

    // Varsayilan olarak tekli kontrol modu
    setCheckMode("single");

    // Gruplari otomatik yükle
    loadGroups();


    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        document.querySelectorAll('.custom-dropdown').forEach(dropdown => {
            if (!dropdown.contains(e.target)) {
                const menu = dropdown.querySelector('.dropdown-menu');
                const trigger = dropdown.querySelector('.dropdown-trigger');
                if (menu && menu.classList.contains('show')) {
                    menu.classList.remove('show');
                    trigger.classList.remove('active');
                }
            }
        });
    });
});

// Custom dropdown functions
function toggleDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    const menu = dropdown.querySelector('.dropdown-menu');
    const trigger = dropdown.querySelector('.dropdown-trigger');
    
    // Close other dropdowns
    document.querySelectorAll('.custom-dropdown').forEach(d => {
        if (d.id !== dropdownId) {
            const m = d.querySelector('.dropdown-menu');
            const t = d.querySelector('.dropdown-trigger');
            if (m && m.classList.contains('show')) {
                m.classList.remove('show');
                t.classList.remove('active');
            }
        }
    });
    
    menu.classList.toggle('show');
    trigger.classList.toggle('active');
}

function selectDropdownOption(dropdownId, value, text) {
    const dropdown = document.getElementById(dropdownId);
    const menu = dropdown.querySelector('.dropdown-menu');
    const trigger = dropdown.querySelector('.dropdown-trigger');
    const textSpan = trigger.querySelector('.dropdown-text');
    const hiddenSelect = dropdown.parentElement.querySelector('.hidden-select');
    
    textSpan.textContent = text;
    menu.classList.remove('show');
    trigger.classList.remove('active');
    
    if (hiddenSelect) {
        hiddenSelect.value = value;
        hiddenSelect.dispatchEvent(new Event('change'));
    }
    
    // Update selected state
    dropdown.querySelectorAll('.dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    event.target.classList.add('selected');
}

function filterDropdown(dropdownId, searchTerm) {
    const dropdown = document.getElementById(dropdownId);
    const options = dropdown.querySelectorAll('.dropdown-option');
    searchTerm = searchTerm.toLowerCase();
    
    options.forEach(opt => {
        const text = opt.textContent.toLowerCase();
        opt.style.display = text.includes(searchTerm) ? 'flex' : 'none';
    });
}

function updateDropdownOptions(dropdownId, options, onSelect) {
    const dropdown = document.getElementById(dropdownId);
    const optionsContainer = dropdown.querySelector('.dropdown-options');
    const trigger = dropdown.querySelector('.dropdown-trigger');
    const textSpan = trigger.querySelector('.dropdown-text');
    
    optionsContainer.innerHTML = '';
    
    if (options.length === 0) {
        optionsContainer.innerHTML = '<div class="dropdown-option" style="color: rgba(255,255,255,0.5); cursor: default;">Seçenek yok</div>';
        return;
    }
    
    options.forEach((opt, index) => {
        const div = document.createElement('div');
        div.className = 'dropdown-option';
        div.innerHTML = opt.label || opt.text || opt;
        div.onclick = function() {
            const value = opt.value !== undefined ? opt.value : (opt.link || opt);
            const text = opt.label || opt.text || opt;
            textSpan.textContent = text;
            
            // Update hidden select
            const hiddenSelect = dropdown.closest('.mb-2').querySelector('.hidden-select');
            if (hiddenSelect) {
                hiddenSelect.value = value;
                hiddenSelect.dispatchEvent(new Event('change'));
            }
            
            // Close dropdown
            const menu = dropdown.querySelector('.dropdown-menu');
            menu.classList.remove('show');
            trigger.classList.remove('active');
            
            // Run callback
            if (onSelect) onSelect(value);
        };
        optionsContainer.appendChild(div);
    });
}

function fetchSharers(silent = false) {
    const postSelect = document.getElementById("postSelect");
    if (!postSelect) return;
    
    const dropdownText = document.querySelector('#postDropdown .dropdown-text');
    if (dropdownText && dropdownText.textContent === "Paylaşımlar yükleniyor...") {
        if (!silent) alert("Paylaşımlar henüz yükleniyor, lütfen bekleyin.");
        return;
    }

    const posts = window.allFetchedPosts || [];
    const sharers = new Set();
    
    posts.forEach(p => {
        const sender = p.username;
        if (sender) {
            sharers.add(sender);
        }
    });

    const textarea = document.getElementById("grup_uye");

    if (sharers.size === 0) {
        if (!silent) alert("Seçili tarihte grupta paylaşım yapan kimse bulunamadı.");
        if (textarea) {
            textarea.value = "";
            if (window.updateUserCount) window.updateUserCount();
        }
        return;
    }

    if (textarea) {
        textarea.value = Array.from(sharers).join("\n");
        if (window.updateUserCount) {
            window.updateUserCount();
        }
    }
}

function handleSharersCheckbox() {
    const isChecked = document.getElementById("onlySharersCheck")?.checked;
    if (isChecked) {
        fetchSharers();
    } else {
        const textarea = document.getElementById("grup_uye");
        if (textarea && window.fullGroupMembers && window.fullGroupMembers.length > 0) {
            textarea.value = window.fullGroupMembers.join("\n");
            if (window.updateUserCount) window.updateUserCount();
        }
    }
}

// Global scope bindings
window.fullGroupMembers = [];
window.toggleDropdown = toggleDropdown;
window.selectDropdownOption = selectDropdownOption;
window.filterDropdown = filterDropdown;
window.updateDropdownOptions = updateDropdownOptions;
window.toggleFavorite = toggleFavorite;
window.fetchSharers = fetchSharers;
window.handleSharersCheckbox = handleSharersCheckbox;

// Re-Login for Active Token Function
window.reloginActiveToken = async function() {
    const btn = document.getElementById("reloginActiveBtn");
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Yenileniyor...';
    btn.disabled = true;

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const response = await fetch('/api/relogin_active', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        const data = await response.json();
        
        if (data.ok) {
            btn.innerHTML = '<i class="fas fa-check me-2"></i> Basarili!';
            btn.style.background = 'rgba(39, 174, 96, 0.2)';
            btn.style.color = '#2ecc71';
            btn.style.borderColor = 'rgba(39, 174, 96, 0.4)';
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            alert("Re-Login basarisiz: " + (data.message || "Bilinmeyen hata"));
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (error) {
        alert("Baglanti hatasi: " + error);
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};


function getIstanbulDateStr() {
    const options = { timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit' };
    const formatter = new Intl.DateTimeFormat('en-CA', options);
    return formatter.format(new Date());
}

function selectPostInUI(postUrl) {
    const postSelect = document.getElementById("postSelect");
    const dropdownText = document.querySelector('#postDropdown .dropdown-text');
    if (!postSelect) return;
    
    postSelect.value = postUrl;
    
    // Find option and update dropdown text
    const selectedOpt = Array.from(postSelect.options).find(opt => opt.value === postUrl);
    if (selectedOpt && dropdownText) {
        dropdownText.textContent = selectedOpt.text;
    }
    
    postSelect.dispatchEvent(new Event('change'));
}

function saveSelectedPostToDb(threadId, dateStr, postUrl) {
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';
    
    fetch('/api/save_selected_post', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            thread_id: threadId,
            date: dateStr,
            post_url: postUrl
        })
    })
    .then(r => r.json())
    .then(res => {
        if (res.success) {
            console.log("Seçilen post veritabanına başarıyla kaydedildi.");
        } else {
            console.error("Seçilen post veritabanına kaydedilemedi.");
        }
    })
    .catch(err => {
        console.error("Seçilen post veritabanı kayıt hatası:", err);
    });
}

function handleAutoSelect(threadId) {
    const lowLikesChecked = document.getElementById("lowLikesCheck")?.checked;
    const dateFilter = document.getElementById("dateFilter")?.value || "yesterday";
    
    if (lowLikesChecked || (dateFilter !== "yesterday" && dateFilter !== "today") || window._checkMode !== "single") {
        return;
    }
    
    const todayStr = getIstanbulDateStr();
    
    fetch(`/api/get_selected_post?thread_id=${threadId}&date=${todayStr}`)
        .then(r => r.json())
        .then(res => {
            let matchedPostUrl = null;
            if (res.success && res.post_url) {
                const chosenPost = (window.allFetchedPosts || []).find(p => p.url === res.post_url);
                if (chosenPost) {
                    const isRecent = chosenPost.is_recent === true;
                    if (isRecent) {
                        matchedPostUrl = res.post_url;
                        console.log("Veritabanından önceden seçilen post yüklendi:", matchedPostUrl);
                    } else {
                        console.log("Veritabanındaki post eski tarihli olduğu için yüklenmedi:", res.post_url);
                    }
                }
            }
            
            if (matchedPostUrl) {
                selectPostInUI(matchedPostUrl);
                
                // Seçilen post veritabanından yüklendiğinde canlı kontrolü başlatmak isteyip istemediğini soran modalı aç
                const modal = document.getElementById("autoRunResultModal");
                if (modal) {
                    modal.classList.add("show");
                }
            } else {
                const onlySharersChecked = document.getElementById("onlySharersCheck")?.checked;
                let candidate = null;
                
                if (!onlySharersChecked) {
                    const memberCount = window.currentGroupMemberCount || (window.fullGroupMembers ? window.fullGroupMembers.length : 30);
                    const limit90 = Math.floor(memberCount * 0.9);
                    
                    candidate = (window.allFetchedPosts || []).find(p => {
                        const commentsOpen = p.comments_disabled === false;
                        const commentCountValid = p.comment_count === undefined || p.comment_count === -1 || p.comment_count >= 3;
                        const isRecent = p.is_recent === true;
                        const hasManyMissing = p.comment_count !== undefined && p.comment_count !== -1 && p.comment_count < limit90;
                        return commentsOpen && commentCountValid && isRecent && hasManyMissing;
                    });
                    
                    if (!candidate) {
                        const recentPosts = (window.allFetchedPosts || []).filter(p => {
                            const commentsOpen = p.comments_disabled === false;
                            const commentCountValid = p.comment_count === undefined || p.comment_count === -1 || p.comment_count >= 3;
                            const isRecent = p.is_recent === true;
                            return commentsOpen && commentCountValid && isRecent;
                        });
                        
                        if (recentPosts.length > 0) {
                            candidate = recentPosts.reduce((prev, curr) => {
                                const prevCount = prev.comment_count !== undefined && prev.comment_count !== -1 ? prev.comment_count : 9999;
                                const currCount = curr.comment_count !== undefined && curr.comment_count !== -1 ? curr.comment_count : 9999;
                                return currCount < prevCount ? curr : prev;
                            });
                            console.log("En az yorumlu post seçildi (%90 sınırı aşıldığı için):", candidate.url);
                        }
                    }
                } else {
                    candidate = (window.allFetchedPosts || []).find(p => {
                        const commentsOpen = p.comments_disabled === false;
                        const commentCountValid = p.comment_count === undefined || p.comment_count === -1 || p.comment_count >= 3;
                        const isRecent = p.is_recent === true;
                        return commentsOpen && commentCountValid && isRecent;
                    });
                }
                
                if (candidate) {
                    console.log("Kriterlere uyan ilk post otomatik seçildi:", candidate.url);
                    selectPostInUI(candidate.url);
                    saveSelectedPostToDb(threadId, todayStr, candidate.url);
                } else if ((window.allFetchedPosts || []).length > 0) {
                    const fallback = (window.allFetchedPosts || []).find(p => p.is_recent === true);
                    if (fallback) {
                        console.log("Kriterlere uyan post bulunamadı, fallback olarak ilk yakın tarihli post seçildi:", fallback.url);
                        selectPostInUI(fallback.url);
                        saveSelectedPostToDb(threadId, todayStr, fallback.url);
                    } else {
                        console.log("Yakın tarihli (dün veya bugün) hiçbir paylaşım bulunamadığı için otomatik seçim yapılmadı.");
                    }
                }
            }
        })
        .catch(err => {
            console.error("Otomatik seçim / veritabanı okuma hatası:", err);
        });
}

window.getIstanbulDateStr = getIstanbulDateStr;
window.handleAutoSelect = handleAutoSelect;
window.saveSelectedPostToDb = saveSelectedPostToDb;


function closeAutoRunModal() {
    const modal = document.getElementById("autoRunResultModal");
    if (modal) {
        modal.classList.remove("show");
    }
}

function viewCachedResult() {
    closeAutoRunModal();
    const checkForm = document.getElementById("checkForm");
    if (checkForm) {
        checkForm.submit();
    }
}

window.closeAutoRunModal = closeAutoRunModal;
window.viewCachedResult = viewCachedResult;

