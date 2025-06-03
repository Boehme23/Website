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
let deviceId = null;
let currentPlaylistUris = []; // Your new array for URIs
let allFetchedTracksData = []; // NEW: Store the full track objects here
let currentPlayingTrackIndex = -1; // To keep track of the current song in the list

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
    currentPlaylistUris = tracks.map(track => track.uri);
    allFetchedTracksData = tracks; // Store the full track objects globally

    if (scrollableResultsBox) {
        console.log("Clearing scrollableResultsBox.");
        scrollableResultsBox.innerHTML = '';
    } else {
        console.error('Error: scrollableResultsBox element not found in displaySearchResults!');
        return;
    }

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

    // This part MUST be inside the function, after the loop finishes adding buttons
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

    const trackIndex = currentPlaylistUris.indexOf(trackUri);

    // This check is good for preventing re-playing the same track
    if (trackIndex !== -1 && trackIndex === currentPlayingTrackIndex) { // Only return if it's the same track being explicitly clicked
        console.log('Track already playing or re-clicked:', trackUri);
        // You might want to toggle play/pause here instead, but that requires checking player state.
        // For now, simply return.
        return;
    }

    // Update UI to highlight the new track
    document.querySelectorAll('.track-item').forEach(item => {
        item.classList.remove('playing');
    });

    const activeButton = document.querySelector(`.play-button[data-uri="${trackUri}"]`);
    if (activeButton) {
        const item = activeButton.closest('.track-item');
        if (item) item.classList.add('playing');
    }

    let requestBody;
    if (trackIndex === -1) {
        console.error("Track URI not found in currentPlaylistUris. Cannot set offset. Playing single track as fallback.");
        requestBody = {
            device_id: deviceId,
            uris: [trackUri]
        };
        currentPlayingTrackIndex = -1; // Reset as we're not in a known playlist context
    } else {
        currentPlayingTrackIndex = trackIndex;
        requestBody = {
            device_id: deviceId,
            uris: currentPlaylistUris, // Pass the entire list of URIs
            offset: {
                position: trackIndex
            },
            position_ms: 0
        };
    }

    console.log("Attempting to play track with JSON body:", JSON.stringify(requestBody));

    try {
        const response = await fetch('/disney/play_track', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + currentAccessToken
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to play track: ${response.status} ${response.statusText} - ${errorText}`);
        }

        console.log('Playing track:', trackUri);

        const currentTrackData = allFetchedTracksData.find(t => t.uri === trackUri);
        if (currentTrackData) {
            currentTrackNameSpan.innerText = currentTrackData.name;
            currentArtistNameSpan.innerText = currentTrackData.artists.map(a => a.name).join(', ');
        } else {
            currentTrackNameSpan.innerText = 'Unknown Track';
            currentArtistNameSpan.innerText = 'Unknown Artist';
        }

        togglePlayPauseButton.innerText = 'Pause';

    } catch (error) {
        console.error('Error playing track:', error);
        alert(`Failed to play track: ${error.message || 'See console for more details.'}`);
    }
}


window.onSpotifyWebPlaybackSDKReady = () => {
    const player = new Spotify.Player({
        name: 'Disney Web Player',
        getOAuthToken: cb => { cb(currentAccessToken); },
        volume: 0.5
    });

    // Error handling
    player.addListener('initialization_error', ({ message }) => { console.error('SDK Init Error:', message); });
    player.addListener('authentication_error', ({ message }) => { console.error('SDK Auth Error:', message); });
    player.addListener('account_error', ({ message }) => { console.error('SDK Account Error:', message); });
    player.addListener('playback_error', ({ message }) => { console.error('SDK Playback Error:', message); });

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

    // Ready - THIS IS WHERE DEVICE_ID BECOMES AVAILABLE
    player.addListener('ready', ({ device_id }) => {
        console.log('Ready with Device ID', device_id);
        deviceId = device_id; // Set the global deviceId here

        // Transfer playback to our new device ONLY AFTER it's ready
        fetch('/disney/transfer_playback', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + currentAccessToken
            },
            body: JSON.stringify({
                device_ids: [deviceId],
                play: false
            })
        }).then(response => {
            if (!response.ok) {
                console.error('Failed to transfer playback:', response.statusText);
            } else {
                console.log('Playback transfer request sent successfully.');
            }
        }).catch(error => {
            console.error('Error during playback transfer fetch:', error);
        });
    });

    // Not Ready
    player.addListener('not_ready', ({ device_id }) => {
        console.log('Device ID has gone offline', device_id);
        deviceId = null;
    });

    // *** IMPORTANT: ONLY CALL player.connect() ONCE HERE ***
    player.connect().then(success => {
        if (success) {
            console.log('Spotify Web Playback SDK successfully connected.');
            // The 'ready' listener will fire if connection is successful and deviceId is available.
        } else {
            console.error('Spotify Web Playback SDK failed to connect.');
        }
    }).catch(error => {
        console.error('Error connecting Spotify Web Playback SDK:', error);
    });


    // Event listeners for control buttons (player must be defined here)
    togglePlayPauseButton.addEventListener('click', () => {
        player.togglePlay();
    });

    nextTrackButton.addEventListener('click', () => {
        console.log("Next button clicked. Player:", player);
        if (player) {
            player.nextTrack();
        } else {
            console.warn("Spotify Player not available for next track.");
        }
    });

    prevTrackButton.addEventListener('click', () => {
        console.log("Previous button clicked. Player:", player);
        if (player) {
            player.previousTrack();
        } else {
            console.warn("Spotify Player not available for previous track.");
        }
    });
}; // <-- THIS IS THE MISSING CLOSING '});' FOR window.onSpotifyWebPlaybackSDKReady

// Check if we have an access token in the URL or sessionStorage
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const accessTokenFromUrl = params.get('access_token');

    if (accessTokenFromUrl) {
        sessionStorage.setItem('spotify_access_token', accessTokenFromUrl);
        currentAccessToken = accessTokenFromUrl;
        window.history.replaceState(null, '', window.location.pathname);
        showLoggedInContent(accessTokenFromUrl);
    } else if (sessionStorage.getItem('spotify_access_token')) {
        currentAccessToken = sessionStorage.getItem('spotify_access_token');
        showLoggedInContent(currentAccessToken);
    } else {
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
                // Handle 401 Unauthorized here if needed for token expiration
                // This is a good place to trigger re-login or clear token
                // if (response.status === 401) {
                //     alert('Session expired. Please log in again.');
                //     sessionStorage.removeItem('spotify_access_token');
                //     location.reload();
                // }
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

    // No need to call window.onSpotifyWebPlaybackSDKReady() here.
    // The SDK itself calls it when it's ready.
    // Keeping this line might cause issues if the SDK isn't fully loaded yet.
    // if (window.Spotify && window.onSpotifyWebPlaybackSDKReady) {
    //     window.onSpotifyWebPlaybackSDKReady();
    // }
}

// This block was previously outside any function scope.
// It likely belongs inside a fetch .catch() or a specific error handler.
// For now, it's commented out as it caused a syntax error being freestanding.
// if (response.status === 401) {
//     alert('Session expired. Please log in again.');
//     sessionStorage.removeItem('spotify_access_token');
//     location.reload();
// }