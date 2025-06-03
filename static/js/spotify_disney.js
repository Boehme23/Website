const loginButton = document.getElementById('login-button');
const loggedInContent = document.getElementById('logged-in-content');
const displayNameSpan = document.getElementById('display-name');
const searchButton = document.getElementById('search-button');
const resultsDiv = document.getElementById('results'); // Main container for results
const togglePlayPauseButton = document.getElementById('togglePlayPause');
const nextTrackButton = document.getElementById('nextTrack');
const prevTrackButton = document.getElementById('prevTrack');
const currentTrackNameSpan = document.getElementById('current-track-name');
const currentArtistNameSpan = document.getElementById('current-artist-name');

// Get a reference to the specific element that will be scrollable
const scrollableResultsBox = document.getElementById('scrollable-results-box');

// Get a reference to the message/heading element within resultsDiv
// Assuming your HTML is: <div id="results"><h3 id="results-message"></h3><div id="scrollable-results-box"></div></div>
const resultsMessageElement = document.getElementById('results-message'); // <-- NEW: Get message element


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

    // --- IMPORTANT CHANGES HERE ---
    // Update the message element with a "Searching..." message
    if (resultsMessageElement) {
        resultsMessageElement.innerText = 'Searching for Disney music...';
    } else {
        // Fallback: if no dedicated message element, clear resultsDiv and add a temporary one
        resultsDiv.innerHTML = '<h3>Searching for Disney music...</h3>';
    }

    // Always clear the scrollable box at the start of a new search
    if (scrollableResultsBox) { // Check if it exists before trying to clear
        scrollableResultsBox.innerHTML = '';
    }
    // --- END IMPORTANT CHANGES ---

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
            displaySearchResults(data.tracks); // This function will populate the scrollableResultsBox
            if (resultsMessageElement) {
                resultsMessageElement.innerText = 'Search Results:'; // Set final heading
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


// --- CONSOLIDATED AND CORRECTED displaySearchResults FUNCTION ---
function displaySearchResults(tracks) {
    console.log("displaySearchResults called. Tracks received:", tracks);
    if (scrollableResultsBox) {
        console.log("Clearing scrollableResultsBox.");
        scrollableResultsBox.innerHTML = '';
    } else {
        console.error('Error: scrollableResultsBox element not found in displaySearchResults!');
        return;
    }
    // The heading "Search Results:" should ideally be managed by the searchButton's
    // click listener, as shown above, targeting the resultsMessageElement.
    // If tracks are empty, put the message directly into the scrollable box.
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
        // Append to the scrollable box
        scrollableResultsBox.appendChild(trackItem);
        console.log("Appended track item to scrollableResultsBox.");
    });
        console.log("Finished appending track items.");
        }

    // Make sure to query play buttons from within the scrollable box
    scrollableResultsBox.querySelectorAll('.play-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const trackUri = event.target.dataset.uri;
            playTrack(trackUri);
        });
    });
}
// --- END CONSOLIDATED displaySearchResults FUNCTION ---


async function playTrack(trackUri) {
    if (!deviceId) {
        alert('Spotify Web Playback SDK is not ready or no active device. Please ensure Spotify is open or try refreshing.');
        return;
    }

    const requestBody = {
        device_id: deviceId,
        uris: [trackUri]
    };

    console.log("Attempting to play track with JSON body:", JSON.stringify(requestBody));

    try {
        await fetch('/disney/play_track', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + currentAccessToken
            },
            body: JSON.stringify(requestBody)
        });

        console.log('Playing track:', trackUri);

        const trackName = scrollableResultsBox.querySelector(`button[data-uri="${trackUri}"]`).previousElementSibling.querySelector('div').innerText;
        const artistName = scrollableResultsBox.querySelector(`button[data-uri="${trackUri}"]`).previousElementSibling.querySelector('span').innerText.split(' - ')[0];
        currentTrackNameSpan.innerText = trackName;
        currentArtistNameSpan.innerText = artistName;
        togglePlayPauseButton.innerText = 'Pause';

    } catch (error) {
        console.error('Error playing track:', error);
        alert('Failed to play track. See console for more details.');
    }
}

window.onSpotifyWebPlaybackSDKReady = () => {
    const player = new Spotify.Player({
        name: 'Disney Web Player',
        getOAuthToken: cb => { cb(currentAccessToken); },
        volume: 0.5
    });

    // Error handling
    player.addListener('initialization_error', ({ message }) => { console.error(message); });
    player.addListener('authentication_error', ({ message }) => { console.error(message); });
    player.addListener('account_error', ({ message }) => { console.error(message); });
    player.addListener('playback_error', ({ message }) => { console.error(message); });

    // Playback status updates
    player.addListener('player_state_changed', state => {
        if (!state) {
            return;
        }
        console.log('Player State Changed:', state);
        currentTrackNameSpan.innerText = state.track_window.current_track.name;
        currentArtistNameSpan.innerText = state.track_window.current_track.artists.map(a => a.name).join(', ');
        togglePlayPauseButton.innerText = state.paused ? 'Play' : 'Pause';
    });

    // Ready
    player.addListener('ready', ({ device_id }) => {
        console.log('Ready with Device ID', device_id);
        deviceId = device_id;
        // Transfer playback to our new device
        fetch('/disney/transfer_playback', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + currentAccessToken
            },
            body: JSON.stringify({
                device_ids: [deviceId],
                play: false // Don't start playing immediately
            })
        }).then(response => {
            if (!response.ok) {
                console.error('Failed to transfer playback:', response.statusText);
            }
        });
    });

    // Not Ready
    player.addListener('not_ready', ({ device_id }) => {
        console.log('Device ID has gone offline', device_id);
        deviceId = null;
    });

    // Connect to the player!
    player.connect();

    togglePlayPauseButton.addEventListener('click', () => {
        player.togglePlay();
    });

    nextTrackButton.addEventListener('click', () => {
        player.nextTrack();
    });

    prevTrackButton.addEventListener('click', () => {
        player.previousTrack();
    });
};

// Check if we have an access token in the URL or sessionStorage
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const accessTokenFromUrl = params.get('access_token');

    if (accessTokenFromUrl) {
        sessionStorage.setItem('spotify_access_token', accessTokenFromUrl);
        currentAccessToken = accessTokenFromUrl;
        window.history.replaceState(null, '', window.location.pathname); // Clean URL
        showLoggedInContent(accessTokenFromUrl);
    } else if (sessionStorage.getItem('spotify_access_token')) {
        currentAccessToken = sessionStorage.getItem('spotify_access_token');
        showLoggedInContent(currentAccessToken);
    } else {
        // Not logged in, show login button
        loginButton.style.display = 'block';
        loggedInContent.style.display = 'none';
    }
});

function showLoggedInContent(token) {
    loginButton.style.display = 'none';
    loggedInContent.style.display = 'block';
    currentAccessToken = token;

    fetch('/disney/user_profile?access_token=' + token)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            displayNameSpan.innerText = data.display_name;
        })
        .catch(error => {
            console.error('Error fetching profile:', error);
            displayNameSpan.innerText = 'Error loading profile';
        });

    if (window.Spotify && window.onSpotifyWebPlaybackSDKReady) {
        window.onSpotifyWebPlaybackSDKReady();
    }
}