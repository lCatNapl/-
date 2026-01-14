main
// Универсальные функции для всех страниц
document.addEventListener('DOMContentLoaded', function() {
    // Закрытие уведомлений
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.parentElement.style.opacity = '0';
            setTimeout(() => this.parentElement.remove(), 300);
        });
    });

    // Рейтинг звездочки
    document.querySelectorAll('.rating').forEach(rating => {
        const value = parseFloat(rating.style.getPropertyValue('--rating') || 0);
        rating.title = `${value * 5}/5`;
    });

    // Плавная прокрутка
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
});
