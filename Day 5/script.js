document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const lengthSlider = document.getElementById('length');
  const lengthValue = document.getElementById('length-value');
  const passwordDisplay = document.getElementById('password-display');
  const generateButton = document.getElementById('generate-button');
  const copyButton = document.getElementById('copy-button');
  const copyIcon = document.getElementById('copy-icon');
  const copyMessage = document.getElementById('copy-message');

  // Checkboxes
  const uppercaseCheckbox = document.getElementById('uppercase');
  const lowercaseCheckbox = document.getElementById('lowercase');
  const numbersCheckbox = document.getElementById('numbers');
  const symbolsCheckbox = document.getElementById('symbols');

  // Strength Indicator
  const strengthText = document.getElementById('strength-text');
  const strengthBars = document.querySelectorAll('#strength-bars div');

  // Character sets
  const charSets = {
    uppercase: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    lowercase: 'abcdefghijklmnopqrstuvwxyz',
    numbers: '0123456789',
    symbols: '!@#$%^&*()_+-=[]{}|;:,.<>?',
  };

  // Update Password Strength Indicator
  const updateStrengthIndicator = () => {
    let score = 0;
    if (uppercaseCheckbox.checked) score++;
    if (lowercaseCheckbox.checked) score++;
    if (numbersCheckbox.checked) score++;
    if (symbolsCheckbox.checked) score++;

    const length = parseInt(lengthSlider.value);
    if (length >= 12) score++;
    if (length >= 16) score++;

    let strength = '';
    let barColors = [];

    if (score <= 2) {
      strength = 'WEAK';
      barColors = ['bg-red-500'];
    } else if (score <= 4) {
      strength = 'MEDIUM';
      barColors = ['bg-yellow-500', 'bg-yellow-500'];
    } else {
      strength = 'STRONG';
      barColors = [
        'bg-emerald-500',
        'bg-emerald-500',
        'bg-emerald-500',
        'bg-emerald-500',
      ];
    }

    // For very low scores, can show a different text
    if (score < 2 || (length < 8 && score < 3)) {
      strength = 'TOO WEAK';
      barColors = ['bg-red-500'];
    }

    strengthText.textContent = strength;
    strengthBars.forEach((bar, index) => {
      if (index < barColors.length) {
        bar.className = `h-6 w-2 rounded-sm ${
          barColors[index] || barColors[0]
        }`;
      } else {
        bar.className = 'h-6 w-2 rounded-sm bg-slate-700';
      }
    });
  };

  // Generate Password Logic
  const generatePassword = () => {
    const length = parseInt(lengthSlider.value);
    let characterPool = '';
    let password = '';
    const options = [];

    if (uppercaseCheckbox.checked) {
      characterPool += charSets.uppercase;
      options.push('uppercase');
    }
    if (lowercaseCheckbox.checked) {
      characterPool += charSets.lowercase;
      options.push('lowercase');
    }
    if (numbersCheckbox.checked) {
      characterPool += charSets.numbers;
      options.push('numbers');
    }
    if (symbolsCheckbox.checked) {
      characterPool += charSets.symbols;
      options.push('symbols');
    }

    if (characterPool === '') {
      passwordDisplay.textContent = 'Select options';
      updateStrengthIndicator(); // Update strength even if no options
      return;
    }

    // Ensure at least one of each selected type is included
    let guaranteedChars = '';
    options.forEach((option) => {
      const charSet = charSets[option];
      guaranteedChars += charSet[Math.floor(Math.random() * charSet.length)];
    });

    // Fill the rest of the password
    for (let i = guaranteedChars.length; i < length; i++) {
      const randomIndex = Math.floor(Math.random() * characterPool.length);
      password += characterPool[randomIndex];
    }

    // Combine and shuffle
    password = guaranteedChars + password;
    password = password
      .split('')
      .sort(() => 0.5 - Math.random())
      .join('');

    passwordDisplay.textContent = password;
    updateStrengthIndicator();
  };

  // Update length display on slider input
  lengthSlider.addEventListener('input', (e) => {
    lengthValue.textContent = e.target.value;
    updateStrengthIndicator();
  });

  // Update strength indicator when options change
  [
    uppercaseCheckbox,
    lowercaseCheckbox,
    numbersCheckbox,
    symbolsCheckbox,
  ].forEach((checkbox) => {
    checkbox.addEventListener('change', updateStrengthIndicator);
  });

  // Copy to Clipboard
  copyButton.addEventListener('click', () => {
    const password = passwordDisplay.textContent;
    if (!password || password === 'Select options') return;

    // Using document.execCommand as a fallback for iframe environments
    const textArea = document.createElement('textarea');
    textArea.value = password;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      copyIcon.classList.add('hidden');
      copyMessage.classList.remove('hidden');

      setTimeout(() => {
        copyIcon.classList.remove('hidden');
        copyMessage.classList.add('hidden');
      }, 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
    document.body.removeChild(textArea);
  });

  // Event Listeners
  generateButton.addEventListener('click', generatePassword);

  // Initial state setup
  generatePassword();
});