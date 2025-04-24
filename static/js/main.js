document.addEventListener('DOMContentLoaded', function() {
    // Tarih formatlama
    const dates = document.querySelectorAll('.date');
    dates.forEach(dateElement => {
        const rawDate = dateElement.textContent;
        const formattedDate = new Date(rawDate).toLocaleDateString('tr-TR');
        dateElement.textContent = formattedDate;
    });

    // Flash mesajlarını otomatik kapatma
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 3000);
    });

    // Form onayları
    const deleteForms = document.querySelectorAll('form[action*="/delete"]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', e => {
            if (!confirm('Bu işlem geri alınamaz. Devam etmek istiyor musunuz?')) {
                e.preventDefault();
            }
        });
    });
});