document.getElementById("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const submitBtn = document.getElementById("submitBtn");
    const loadingMessage = document.getElementById("loadingMessage");
    const successMessage = document.getElementById("successMessage");
    const errorMessage = document.getElementById("errorMessage");

    const username = document.getElementById("kullanici_adi").value;
    const password = document.getElementById("sifre").value;
    const androidId = document.getElementById("android_id").value;
    const userAgent = document.getElementById("user_agent").value;
    const deviceId = document.getElementById("device_id").value;

    if (!username.trim() || !password.trim() || !androidId.trim() || !userAgent.trim() || !deviceId.trim()) {
        errorMessage.style.display = "block";
        document.getElementById("errorText").textContent = "Tum alanlar zorunludur: kullanici adi, sifre, android id, user agent, device id.";
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Yukleniyor...';
    loadingMessage.style.display = "block";
    successMessage.style.display = "none";
    errorMessage.style.display = "none";

    try {
        const formData = new FormData();
        formData.append("kullanici_adi", username);
        formData.append("sifre", password);
        formData.append("android_id", androidId);
        formData.append("user_agent", userAgent);
        formData.append("device_id", deviceId);

        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const response = await fetch("/giris_yaps", {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrfToken
            }
        });
        const data = await response.json();

        loadingMessage.style.display = "none";

        if (data.token && data.android_id_yeni) {
            successMessage.style.display = "block";
            document.getElementById("successText").textContent = "Token basariyla alindi! Ana sayfaya yonlendiriliyorsunuz...";
            setTimeout(() => {
                window.location.href = "/";
            }, 2000);
            return;
        }

        if (data.message) {
            throw new Error(data.message);
        }
        throw new Error("Token alinamadi");
    } catch (_error) {
        loadingMessage.style.display = "none";
        errorMessage.style.display = "block";
        document.getElementById("errorText").textContent = _error.message || "Giris basarisiz! Bilgileri kontrol edin.";
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Giris Yap ve Token Al';
    }
});
