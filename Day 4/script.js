// Custom Tailwind Configuration
tailwind.config = {
    theme: {
        extend: {
            colors: {
                'ivory': '#FDFDFB', // Main background
                'charcoal': '#1A1A1A', // Deep text, dark backgrounds
                'soft-gold': '#C0A067', // Accents, buttons, borders
                'dark-gold': '#A78B58', // Hover for gold
                'light-gray': '#F5F5F5', // Secondary backgrounds
            },
            fontFamily: {
                'sans': ['Poppins', 'sans-serif'],
                'display': ['Playfair Display', 'serif'],
            }
        }
    },
}

document.addEventListener('DOMContentLoaded', function () {
    // --- Initialize AOS (Animate on Scroll) ---
    AOS.init({
        duration: 1000,
        once: true,
        offset: 50,
    });

    // --- Initialize Lucide Icons ---
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    } else {
        console.error('Lucide icons script not loaded or failed to load.');
    }

    // --- Set Current Year in Footer ---
    document.getElementById('current-year').textContent = new Date().getFullYear();

    // --- Header Scroll Effect ---
    const header = document.getElementById('navbar');
    const logo = document.getElementById('logo');
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const desktopNavLinks = document.querySelectorAll('.nav-link-desktop');
    const desktopNavCta = document.getElementById('nav-cta-desktop');

    const handleScroll = () => {
        const isScrolled = window.scrollY > 50;
        const isOpen = hamburgerBtn.classList.contains('open');

        if (isScrolled) {
            header.classList.add('scrolled');
            logo.classList.remove('text-ivory');
            logo.classList.add('text-charcoal');
            desktopNavLinks.forEach(link => {
                link.classList.remove('text-ivory/80');
                link.classList.add('text-charcoal/80');
            });
            desktopNavCta.classList.remove('bg-ivory', 'text-charcoal');
            desktopNavCta.classList.add('bg-charcoal', 'text-ivory');
        } else {
            header.classList.remove('scrolled');
            logo.classList.add('text-ivory');
            logo.classList.remove('text-charcoal');
            desktopNavLinks.forEach(link => {
                link.classList.add('text-ivory/80');
                link.classList.remove('text-charcoal/80');
            });
            desktopNavCta.classList.add('bg-ivory', 'text-charcoal');
            desktopNavCta.classList.remove('bg-charcoal', 'text-ivory');
        }

        // Handle hamburger icon color
        if (!isOpen) {
            hamburgerBtn.querySelectorAll('span').forEach(span => {
                if (isScrolled) {
                    span.classList.remove('bg-ivory');
                    span.classList.add('bg-charcoal');
                } else {
                    span.classList.add('bg-ivory');
                    span.classList.remove('bg-charcoal');
                }
            });
        }
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll(); // Run on load to set initial state

    // --- Full-screen Nav Toggle ---
    const navOverlay = document.getElementById('nav-overlay');
    hamburgerBtn.addEventListener('click', () => {
        const isOpen = hamburgerBtn.classList.toggle('open');
        navOverlay.classList.toggle('open');
        document.body.classList.toggle('overflow-hidden');

        // On toggle, force hamburger color
        hamburgerBtn.querySelectorAll('span').forEach(span => {
            if (isOpen) {
                span.classList.remove('bg-charcoal');
                span.classList.add('bg-ivory');
            } else {
                // On close, re-run scroll check to set correct color
                handleScroll();
            }
        });
    });
    // Close overlay when a link is clicked
    navOverlay.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            hamburgerBtn.classList.remove('open');
            navOverlay.classList.remove('open');
            document.body.classList.remove('overflow-hidden');
            handleScroll();
        });
    });


    // --- Scroll Indicator ---
    const scrollIndicator = document.getElementById('scroll-indicator');
    window.addEventListener('scroll', () => {
        const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
        if (scrollHeight > clientHeight) {
            const scrollPercent = (scrollTop / (scrollHeight - clientHeight)) * 100;
            scrollIndicator.style.width = `${scrollPercent}%`;
        }
    });

    // --- Number Counter for Statistics ---
    const counters = [
        { id: 'stat-1', target: 12, duration: 2000 },
        { id: 'stat-2', target: 25, duration: 2000 },
        { id: 'stat-3', target: 98, duration: 2000 }
    ];

    const animateCounter = (el, target, duration) => {
        let start = 0;
        let startTime = null;

        const step = (timestamp) => {
            if (!startTime) startTime = timestamp;
            const progress = timestamp - startTime;
            const percentage = Math.min(progress / duration, 1);

            start = Math.floor(percentage * target);
            el.textContent = start;

            if (percentage < 1) {
                window.requestAnimationFrame(step);
            } else {
                el.textContent = target; // Ensure it ends on the exact target
            }
        };
        window.requestAnimationFrame(step);
    };

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                counters.forEach(counter => {
                    const el = document.getElementById(counter.id);
                    if (el && !el.dataset.animated) {
                        animateCounter(el, counter.target, counter.duration);
                        el.dataset.animated = true; // Mark as animated
                    }
                });
                observer.disconnect(); // Stop observing once animated
            }
        });
    }, { threshold: 0.5 }); // Trigger when 50% visible

    const statSection = document.querySelector('#stat-1'); // Observe the first stat
    if (statSection) {
        observer.observe(statSection.parentElement);
    }

    // --- Testimonials Slider ---
    if (typeof Swiper !== 'undefined') {
        new Swiper('.testimonial-slider', {
            loop: true,
            slidesPerView: 1,
            spaceBetween: 30,
            autoplay: {
                delay: 5000,
                disableOnInteraction: false,
            },
            pagination: {
                el: '.swiper-pagination',
                clickable: true,
            },
            breakpoints: {
                768: {
                    slidesPerView: 2,
                    spaceBetween: 30,
                },
            },
        });
    } else {
        console.error('Swiper.js not loaded or failed to load.');
    }

    /* ================== [ Scroll-to-top code ] ================== */
    const scrollTopBtn = document.getElementById('scrollTopBtn');
    const progressRing = document.getElementById('progress-ring');

    if (scrollTopBtn && progressRing) {
        // Calculate circumference
        const radius = progressRing.r.baseVal.value;
        const circumference = 2 * Math.PI * radius;

        // Set initial stroke-dasharray
        progressRing.style.strokeDasharray = `${circumference} ${circumference}`;

        const handleScrollProgress = () => {
            const scrollTop = window.scrollY;
            const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;

            // 1. Calculate scroll progress
            // Ensure docHeight is not zero to avoid division by zero
            const scrollPercent = docHeight > 0 ? (scrollTop / docHeight) : 0;
            const dashoffset = circumference - (scrollPercent * circumference);
            progressRing.style.strokeDashoffset = dashoffset;

            // 2. Show/hide button
            if (scrollTop > 300) { // Show after 300px of scroll
                scrollTopBtn.classList.add('is-visible');
            } else {
                scrollTopBtn.classList.remove('is-visible');
            }
        };

        window.addEventListener('scroll', handleScrollProgress);
    }
    /* ================== [ End of scroll-to-top code ] ================== */


    // Chatbot Function
    const chatToggleBtn = document.getElementById('chat-toggle-btn');
    const chatbotWindow = document.getElementById('chatbot-window');
    const chatbotCloseBtn = document.getElementById('chatbot-close-btn');
    const chatbotForm = document.getElementById('chatbot-form');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotMessages = document.getElementById('chatbot-messages');

    if (chatToggleBtn && chatbotWindow && chatbotCloseBtn && chatbotForm && chatbotInput && chatbotMessages) {

        // Toggle window visibility
        const toggleChatbot = () => {
            chatbotWindow.classList.toggle('is-visible');
            chatToggleBtn.classList.toggle('is-visible'); // You can style this if needed
            if (chatbotWindow.classList.contains('is-visible')) {
                chatbotInput.focus();
            }
        };

        chatToggleBtn.addEventListener('click', toggleChatbot);
        chatbotCloseBtn.addEventListener('click', toggleChatbot);

        // Handle sending a message
        chatbotForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const messageText = chatbotInput.value.trim();
            if (messageText === "") return;

            // 1. Add user's message
            appendMessage(messageText, 'user');
            chatbotInput.value = "";

            // 2. Add dummy bot reply
            setTimeout(() => {
                appendMessage("Thank you for your message. An agent will be in touch with you shortly regarding your inquiry.", 'bot');
            }, 1000);
        });

        // Function to add a message to the chat window
        const appendMessage = (text, type) => {
            const messageElement = document.createElement('div');
            messageElement.classList.add('chat-message', type);
            messageElement.textContent = text;
            chatbotMessages.appendChild(messageElement);

            // Scroll to bottom
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        };
    }
});