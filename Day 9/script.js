document.addEventListener('DOMContentLoaded', () => {
  // --- 1. Personalization ---
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const name = urlParams.get('name');
    const nameElement = document.getElementById('user-name');
    if (name) {
      const sanitizedName = name.replace(/<[^>]*>?/gm, '');
      if (sanitizedName) {
        nameElement.textContent = sanitizedName;
      }
    }
  } catch (e) {
    console.error('Error processing URL parameters:', e);
  }

  // --- 2. Staggered Reveal Animation ---
  const revealItems = document.querySelectorAll('.reveal-item');
  revealItems.forEach((item, index) => {
    // Use a standard delay for all non-marquee items
    let delay = 1200 + index * 150;

    // Marquee items use their own inline style --delay
    if (item.classList.contains('marquee-container')) {
      delay = 0; // The animation will be handled by the CSS delay
    }

    setTimeout(() => {
      item.classList.add('is-visible');
    }, delay);
  });

  // --- 3. Interactive Image Preview (Desktop Only) ---
  if (window.matchMedia('(min-width: 768px)').matches) {
    const links = document.querySelectorAll('.preview-link');
    const previewContainer = document.getElementById('image-preview-container');
    const previewImage = document.getElementById('preview-image');

    links.forEach((link) => {
      link.addEventListener('mouseenter', () => {
        const imageUrl = link.getAttribute('data-image');
        if (imageUrl) {
          previewImage.src = imageUrl;
          previewContainer.style.opacity = '1';
          previewImage.classList.add('is-panning'); // Add class to start pan/zoom
        }
      });

      link.addEventListener('mouseleave', () => {
        previewContainer.style.opacity = '0';
        previewImage.classList.remove('is-panning'); // Remove class to stop
        // Reset transform to prepare for next hover
        previewImage.style.transition = 'opacity 0.5s ease'; // Only transition opacity on exit
        previewImage.style.transform = 'scale(1.1)';
        // Force reflow to reset transition
        void previewImage.offsetWidth;
        previewImage.style.transition =
          'transform 6s ease-out, opacity 0.5s ease';
      });
    });
  }

  // --- 4. Custom Cursor Logic ---
  const cursorDot = document.querySelector('.custom-cursor-dot');
  const hoverElements = document.querySelectorAll('a, button');

  window.addEventListener('mousemove', (e) => {
    cursorDot.style.left = `${e.clientX}px`;
    cursorDot.style.top = `${e.clientY}px`;
  });

  hoverElements.forEach((el) => {
    el.addEventListener('mouseenter', () =>
      cursorDot.classList.add('cursor-hover')
    );
    el.addEventListener('mouseleave', () =>
      cursorDot.classList.remove('cursor-hover')
    );
  });

  // --- 5. Scroll-Linked Fade Animation ---
  const scrollPanel = document.getElementById('scroll-panel');
  const scrollContent = document.getElementById('scroll-content');

  if (scrollPanel && scrollContent) {
    scrollPanel.addEventListener('scroll', () => {
      if (scrollPanel.scrollTop > 50) {
        scrollContent.classList.add('is-scrolled');
      } else {
        scrollContent.classList.remove('is-scrolled');
      }
    });
  }
});