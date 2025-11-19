// Initialize Lenis for smooth scrolling
const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  direction: 'vertical',
  gestureDirection: 'vertical',
  smooth: true,
  smoothTouch: false,
  touchMultiplier: 2,
});

function raf(time) {
  lenis.raf(time);
  requestAnimationFrame(raf);
}

requestAnimationFrame(raf);

// GSAP Animations
gsap.registerPlugin(ScrollTrigger, TextPlugin);

// Hero content animation
const tl = gsap.timeline();

tl.to('.hero-subtitle', {
  opacity: 1,
  y: 0,
  duration: 1,
  delay: 0.5,
})
  .to('.hero-title', {
    opacity: 1,
    y: 0,
    duration: 1,
  })
  .to('.hero-description', {
    opacity: 1,
    y: 0,
    duration: 1,
  })
  .to('.cta-buttons', {
    opacity: 1,
    y: 0,
    duration: 1,
  })
  .to('.stats', {
    opacity: 1,
    y: 0,
    duration: 1,
  })
  .to('.scroll-indicator', {
    opacity: 1,
    duration: 1,
  });

// Carousel functionality
const carCards = document.querySelectorAll('.car-card');
const prevBtn = document.querySelector('.prev-btn');
const nextBtn = document.querySelector('.next-btn');
let currentCarIndex = 0;

function updateCarousel(index) {
  // Remove active class from all cards
  carCards.forEach((card) => {
    card.classList.remove('active');
  });

  // Add active class to current card
  carCards[index].classList.add('active');

  currentCarIndex = index;
}

// Next car
nextBtn.addEventListener('click', () => {
  const nextIndex = (currentCarIndex + 1) % carCards.length;
  updateCarousel(nextIndex);
});

// Previous car
prevBtn.addEventListener('click', () => {
  const prevIndex = (currentCarIndex - 1 + carCards.length) % carCards.length;
  updateCarousel(prevIndex);
});

// Auto carousel
setInterval(() => {
  const nextIndex = (currentCarIndex + 1) % carCards.length;
  updateCarousel(nextIndex);
}, 5000);

// Counter animation for stats
const statNumbers = document.querySelectorAll('.stat-number');

statNumbers.forEach((stat) => {
  const target = parseInt(stat.textContent);
  let current = 0;
  const increment = target / 50;

  const updateCounter = () => {
    if (current < target) {
      current += increment;
      stat.textContent =
        Math.ceil(current) + (stat.textContent.includes('+') ? '+' : '');
      setTimeout(updateCounter, 50);
    } else {
      stat.textContent = target + (stat.textContent.includes('+') ? '+' : '');
    }
  };

  // Start counter animation when stats become visible
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        updateCounter();
        observer.unobserve(entry.target);
      }
    });
  });

  observer.observe(stat);
});

// Mouse move parallax effect
document.addEventListener('mousemove', (e) => {
  const moveX = (e.clientX - window.innerWidth / 2) * 0.01;
  const moveY = (e.clientY - window.innerHeight / 2) * 0.01;

  gsap.to('.car-card.active', {
    x: moveX,
    y: moveY,
    rotationY: moveX * 0.5,
    duration: 1,
    ease: 'power2.out',
  });

  gsap.to('.shape-1', {
    x: moveX * 5,
    y: moveY * 5,
    duration: 2,
    ease: 'power2.out',
  });

  gsap.to('.shape-2', {
    x: -moveX * 3,
    y: -moveY * 3,
    duration: 2,
    ease: 'power2.out',
  });
});