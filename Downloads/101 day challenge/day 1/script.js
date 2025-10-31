// Parallax effect — background subtly follows mouse
const background = document.querySelector(".background");

window.addEventListener("mousemove", (e) => {
  const x = (e.clientX / window.innerWidth - 0.5) * 20;
  const y = (e.clientY / window.innerHeight - 0.5) * 20;
  background.style.transform = `translate(${x}px, ${y}px) scale(1.05)`;
});

// Reset smooth re-centering when mouse leaves
window.addEventListener("mouseleave", () => {
  background.style.transform = `translate(0px, 0px) scale(1.05)`;
});
