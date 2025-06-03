const loginButton = document.getElementById('login-button');
const loggedInContent = document.getElementById('logged-in-content');
const displayNameSpan = document.getElementById('display-name');
const searchButton = document.getElementById('search-button');
const resultsDiv = document.getElementById('results');
// Make sure you have this reference:
const scrollableResultsBox = document.getElementById('scrollable-results-box'); // <-- Get this element

const togglePlayPauseButton = document.getElementById('togglePlayPause');
const nextTrackButton = document.getElementById('nextTrack');
const prevTrackButton = document.getElementById('prevTrack');
const currentTrackNameSpan = document.getElementById('current-track-name');
const currentArtistNameSpan = document.getElementById('current-artist-name');

let currentAccessToken = '';
let deviceId = null; // Spotify Connect device ID

loginButton.addEventListener('click', () => {
    window.location.href = '/disney/login'; // Redirect to Flask login route
});

searchButton.addEventListener('click', async () => {
    if (!currentAccessToken) {
        alert('Please login with Spotify first!');
        return;
    }

    // IMPORTANT CHANGE HERE:
    // Instead of clearing resultsDiv entirely, clear the scrollable box
    // and put the "Searching..." message in resultsDiv (if you want it outside)
    // OR, better, have a dedicated message element.

    // Option A: Clear scrollable box and update a *specific* message area.
    // Assuming you have an H3 or P tag inside resultsDiv for messages
    // E.g., <div id="results"> <h3 id="results-message"></h3> <div id="scrollable-results-box"></div> </div>
    const resultsMessageElement = resultsDiv.querySelector('h3'); // Assuming your H3 is the message
    if (resultsMessageElement) {
        resultsMessageElement.innerText = 'Searching for Disney music...';
    } else {
        // Fallback if no specific message element, but it's better to have one
        resultsDiv.innerHTML = '<h3>Searching for Disney music...</h3>';
    }
    scrollableResultsBox.innerHTML = ''; // Always clear the track list when a new search starts

    try {
        const response = await fetch('/disney/search_disney_music?access_token=' + currentAccessToken);
        const data = await response.json();

        if (data.tracks.length === 0) {
            if (resultsMessageElement) {
                resultsMessageElement.innerText = 'No tracks found in the Disney playlist.';
            } else {
                resultsDiv.innerHTML = '<h3>No tracks found in the Disney playlist.</h3>';
            }
        } else {
            // This function will handle populating the scrollableResultsBox
            displaySearchResults(data.tracks);
            if (resultsMessageElement) {
                resultsMessageElement.innerText = '<h3>Search Results:</h3>'; // Reset heading after results are displayed
            } else {
                 resultsDiv.innerHTML = '<h3>Search Results:</h3>';
            }
        }
    } catch (error) {
        console.error('Error searching music:', error);
        if (resultsMessageElement) {
            resultsMessageElement.innerText = 'Error searching music.';
        } else {
            resultsDiv.innerHTML = '<h3>Error searching music.</h3>';
        }
    }
});

// ... rest of your JavaScript ...

// Ensure your displaySearchResults function uses scrollableResultsBox
function displaySearchResults(tracks) {
    // Clear the scrollable box, as new results are coming
    scrollableResultsBox.innerHTML = '';

    // The heading for search results should probably be *outside* the scrollable box
    // and managed by the searchButton click listener as shown above.
    // If you always want it here, you can place it like this:
    // resultsDiv.innerHTML = '<h3>Search Results:</h3>'; // This line would still clear resultsDiv,
    // SO, you should only update the specific heading, not the whole div.

    // If you've modified resultsDiv to have a specific message element,
    // you don't need this line here. The header is handled by the searchButton listener.

    if (tracks.length === 0) {
        scrollableResultsBox.innerHTML += '<p>No Disney tracks found.</p>';
        return;
    }

    tracks.forEach(track => {
        const trackItem = document.createElement('div');
        trackItem.classList.add('track-item');
        const albumArt = track.album.images.length > 0 ? track.album.images[0].url : 'https://placehold.co/50x50/cccccc/333333?text=No+Art';
        trackItem.innerHTML = `
            <img src="${albumArt}" alt="${track.name} album art" onerror="this.onerror=null;this.src='https://placehold.co/50x50/cccccc/333333?text=No+Art';">
            <div class="track-info">
                <div>${track.name}</div>
                <span>${track.artists.map(a => a.name).join(', ')} - ${track.album.name}</span>
            </div>
            <button class="play-button" data-uri="${track.uri}">Play</button>
        `;
        scrollableResultsBox.appendChild(trackItem); // Append to the scrollable box
    });

    scrollableResultsBox.querySelectorAll('.play-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const trackUri = event.target.dataset.uri;
            playTrack(trackUri);
        });
    });
}