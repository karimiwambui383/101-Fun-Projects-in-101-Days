document.addEventListener('DOMContentLoaded', function () {

    // 1. AOS Initialization
    AOS.init({
        duration: 800,    // animation duration in ms
        easing: 'ease-in-out', // animation timing function
        once: true,       // whether animation should happen only once - while scrolling down
        mirror: false,    // whether elements should animate out while scrolling past them
        offset: 80,    // offset (in px) from the original trigger point
    });

    // 2. Navbar Scroll Effect
    const navbar = document.getElementById('navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // 3. Testimonials Slider (Swiper)
    if (document.querySelector('.testimonials-slider')) {
        const testimonialsSlider = new Swiper('.testimonials-slider', {
            loop: true,
            grabCursor: true,
            spaceBetween: 30,
            pagination: {
                el: '.swiper-pagination',
                clickable: true,
            },
            breakpoints: {
                768: {
                    slidesPerView: 2,
                },
                1200: {
                    slidesPerView: 3,
                }
            }
        });
    }

    // 4. Gallery Popup (FancyBox)
    if (document.querySelector("[data-fancybox='gallery']")) {
        Fancybox.bind("[data-fancybox='gallery']", {
            // Your custom options
        });
    }

    // 5. Pricing Toggle
    const toggle = document.getElementById('pricing-toggle-switch');
    const monthlyLabel = document.getElementById('monthly-label');
    const yearlyLabel = document.getElementById('yearly-label');
    const prices = document.querySelectorAll('.pricing-card .price');

    if (toggle) {
        toggle.addEventListener('change', () => {
            const isYearly = toggle.checked;

            monthlyLabel.classList.toggle('active', !isYearly);
            yearlyLabel.classList.toggle('active', isYearly);

            prices.forEach(priceEl => {
                const monthlyPrice = priceEl.getAttribute('data-monthly');
                const yearlyPrice = priceEl.getAttribute('data-yearly');

                if (isYearly) {
                    priceEl.innerHTML = `${yearlyPrice}<span>/mo</span>`;
                } else {
                    priceEl.innerHTML = `${monthlyPrice}<span>/mo</span>`;
                }
            });
        });
    }

    // 6. Copyright Year
    const yearSpan = document.getElementById('copyright-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }

    // 7. Scroll to Top
    let scrollToTopButton = document.getElementById("scrollToTopBtn");

    // Show/Hide button on scroll
    window.onscroll = function () {
        if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {
            scrollToTopButton.classList.add("active");
        } else {
            scrollToTopButton.classList.remove("active");
        }
    };

    // Smooth scroll to top on click
    scrollToTopButton.addEventListener('click', function (e) {
        e.preventDefault();
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

});