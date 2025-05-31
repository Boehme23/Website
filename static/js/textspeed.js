const quoteDisplayElement = document.getElementById('quoteDisplay');
const quoteInputElement = document.getElementById('quoteInput');
const startButton = document.getElementById('startButton');
const newTextButton = document.getElementById('newTextButton');
const timeElement = document.getElementById('time');
const wpmElement = document.getElementById('wpm');
const accuracyElement = document.getElementById('accuracy');

let startTime;
let timerInterval;
let currentQuote = '';
let isTyping = false;

// Array of quotes for the test
const quotes = [
    "The quick brown fox jumps over the lazy dog.",
    "Never underestimate the power of a good book.",
    "Programming is thinking, not typing.",
    "The early bird catches the worm.",
    "To be or not to be, that is the question.",
    "In the beginning God created the heavens and the earth.",
    "The only way to do great work is to love what you do.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "The greatest glory in living lies not in never falling, but in rising every time we fall.",
    "The journey of a thousand miles begins with a single step."
];

// Function to get a random quote
function getRandomQuote() {
    return quotes[Math.floor(Math.random() * quotes.length)];
}

// Function to render a new quote
async function renderNewQuote() {
    currentQuote = getRandomQuote();
    quoteDisplayElement.innerHTML = ''; // Clear previous text

    currentQuote.split('').forEach(character => {
        const charSpan = document.createElement('span');
        charSpan.innerText = character;
        quoteDisplayElement.appendChild(charSpan);
    });

    quoteInputElement.value = ''; // Clear input field
    quoteInputElement.disabled = true; // Disable until test starts
    startButton.disabled = false; // Enable start button
    newTextButton.disabled = false; // Enable new text button

    // Reset results display
    timeElement.innerText = '0';
    wpmElement.innerText = '0';
    accuracyElement.innerText = '100';

    // Remove any previous styling classes
    quoteInputElement.classList.remove('correct', 'incorrect');

    isTyping = false;
    clearInterval(timerInterval); // Ensure timer is stopped
}

// Function to start the timer
function startTimer() {
    startTime = new Date();
    timerInterval = setInterval(() => {
        timeElement.innerText = getTimerTime();
    }, 1000);
}

// Function to get elapsed time in seconds
function getTimerTime() {
    return Math.floor((new Date() - startTime) / 1000);
}

// Event listener for input changes
quoteInputElement.addEventListener('input', () => {
    if (!isTyping) {
        startTimer();
        isTyping = true;
    }

    const arrayQuote = quoteDisplayElement.querySelectorAll('span');
    const arrayValue = quoteInputElement.value.split('');

    let correct = true;
    let correctChars = 0;

    arrayQuote.forEach((characterSpan, index) => {
        const character = arrayValue[index];

        if (character == null) {
            characterSpan.classList.remove('correct', 'incorrect');
            correct = false;
        } else if (character === characterSpan.innerText) {
            characterSpan.classList.add('correct');
            characterSpan.classList.remove('incorrect');
            correctChars++;
        } else {
            characterSpan.classList.remove('correct');
            characterSpan.classList.add('incorrect');
            correct = false;
        }
    });

    // Apply color to the input field based on overall correctness
    if (quoteInputElement.value === currentQuote.substring(0, quoteInputElement.value.length)) {
        quoteInputElement.classList.remove('incorrect');
        quoteInputElement.classList.add('correct');
    } else {
        quoteInputElement.classList.remove('correct');
        quoteInputElement.classList.add('incorrect');
    }


    // Check if the user has finished typing
    if (correct && arrayValue.length === currentQuote.length) {
        finishTest();
    }

    // Update WPM and Accuracy in real-time
    updateResults(correctChars, arrayValue.length);
});

// Function to update WPM and Accuracy
function updateResults(correctChars, typedCharsCount) {
    const timeTaken = getTimerTime();
    if (timeTaken === 0) return; // Prevent division by zero

    // Calculate WPM: (Number of characters / 5) / Time in minutes
    const wpm = Math.round((typedCharsCount / 5) / (timeTaken / 60));
    wpmElement.innerText = isNaN(wpm) ? 0 : wpm; // Handle NaN if no chars typed yet

    // Calculate accuracy: (Correct characters / Total typed characters) * 100
    const accuracy = typedCharsCount === 0 ? 100 : Math.round((correctChars / typedCharsCount) * 100);
    accuracyElement.innerText = isNaN(accuracy) ? 100 : accuracy; // Handle NaN
}


// Function to finish the test
function finishTest() {
    clearInterval(timerInterval); // Stop the timer
    quoteInputElement.disabled = true; // Disable input
    startButton.disabled = true; // Disable start button
    newTextButton.disabled = false; // Enable new text button

    const timeTaken = getTimerTime();
    const typedText = quoteInputElement.value;
    const originalText = currentQuote;

    let correctChars = 0;
    for (let i = 0; i < Math.min(typedText.length, originalText.length); i++) {
        if (typedText[i] === originalText[i]) {
            correctChars++;
        }
    }

    // Recalculate final WPM and Accuracy based on full typed text
    const finalWPM = Math.round((typedText.length / 5) / (timeTaken / 60));
    const finalAccuracy = typedText.length === 0 ? 0 : Math.round((correctChars / typedText.length) * 100);

    wpmElement.innerText = isNaN(finalWPM) ? 0 : finalWPM;
    accuracyElement.innerText = isNaN(finalAccuracy) ? 0 : finalAccuracy;

    isTyping = false;
}


// Event listener for Start button
startButton.addEventListener('click', () => {
    quoteInputElement.disabled = false; // Enable input
    quoteInputElement.focus(); // Focus on input field
    startButton.disabled = true; // Disable start button
    newTextButton.disabled = true; // Disable new text button
    startTimer();
    isTyping = true;
});

// Event listener for New Text button
newTextButton.addEventListener('click', renderNewQuote);


// Initialize the game when the page loads
renderNewQuote();
