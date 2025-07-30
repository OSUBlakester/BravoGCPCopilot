document.getElementById('newsButton').addEventListener('click', () => {
    getCurrentEvents('news');
});

document.getElementById('sportsButton').addEventListener('click', () => {
    getCurrentEvents('sports');
});

document.getElementById('entertainmentButton').addEventListener('click', () => {
    getCurrentEvents('movies and music');
});

async function getCurrentEvents(eventType) {
    const response = await fetch('/get-current-events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eventType }),
    });
    const data = await response.json();
    generateLlmButtons(data.summaries);
}

function generateLlmButtons(options) {
    const gridContainer = document.getElementById('gridContainer');
    gridContainer.innerHTML = '';
    currentOptions = options;

    options.forEach(option => {
        const button = document.createElement('button');
        button.textContent = option;
        button.classList.add('llm-button');
        button.addEventListener('click', () => {
            console.log("Button clicked:", option); // Debugging log
            //stopAuditoryScanning(); //ensure that this function is available.
            console.log("speaking llm option");
            speak(option, "system")
                .then(() => {
                    console.log("speak callback triggered");
                    window.location.reload(true);

                    document.addEventListener('DOMContentLoaded', function() {
                        console.log("DOMContentLoaded triggered, starting scanning");
                        //startAuditoryScanning(); //ensure that this function is available.
                    });
                })
                .catch(error => {
                    console.error("speak error", error);
                });
        });
        gridContainer.appendChild(button);
    });
}

async function speak(text, audioType = "system") {
    console.log("Speaking:", text); // Debugging log
    
    // Show splash screen if enabled
    if (typeof showSplashScreen === 'function') {
        showSplashScreen(text);
    }
    
    return new Promise((resolve, reject) => {
        fetch('/play-audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, audioType }),
        })
        .then(response => {
            if (!response.ok) {
                reject(new Error('Failed to play audio'));
            } else {
                resolve();
            }
        })
        .catch(error => {
            console.error('Error playing audio:', error);
            reject(error);
        });
    });
}