const loginButton = document.getElementById('login-button');
const loggedInContent = document.getElementById('logged-in-content');
const displayNameSpan = document.getElementById('display-name');
const searchButton = document.getElementById('search-button');
const resultsDiv = document.getElementById('results');
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
resultsDiv.innerHTML = 'Searching for Disney music...';
try {
const response = await fetch('/search_disney_music?access_token=' + currentAccessToken);
const data = await response.json();
displaySearchResults(data.tracks.items);
} catch (error) {
console.error('Error searching music:', error);
resultsDiv.innerHTML = 'Error searching music.';
}
});

function displaySearchResults(tracks) {
resultsDiv.innerHTML = '<h3>Search Results:</h3>';
if (tracks.length === 0) {
resultsDiv.innerHTML += '<p>No Disney tracks found.</p>';
return;
}
tracks.forEach(track => {
const trackItem = document.createElement('div');
trackItem.classList.add('track-item');
const albumArt = track.album.images.length > 0 ? track.album.images[0].url : 'https://via.placeholder.com/50';
trackItem.innerHTML = `
    <img src="${albumArt}" alt="${track.name} album art">
    <div class="track-info">
        <div>${track.name}</div>
        <span>${track.artists.map(a => a.name).join(', ')} - ${track.album.name}</span>
    </div>
    <button class="play-button" data-uri="${track.uri}">Play</button>
`;
resultsDiv.appendChild(trackItem);
});

resultsDiv.querySelectorAll('.play-button').forEach(button => {
button.addEventListener('click', (event) => {
    const trackUri = event.target.dataset.uri;
    playTrack(trackUri);
});
});
}

async function playTrack(trackUri) {
if (!deviceId) {
alert('Spotify Web Playback SDK is not ready. Please ensure Spotify is open or try refreshing.');
return;
}
try {
await fetch('/play_track', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + currentAccessToken
    },
    body: JSON.stringify({
        device_id: deviceId,
        uris: [trackUri]
    })
});
console.log('Playing track:', trackUri);
// Update current playing info (simplified, could poll Spotify API)
const trackName = resultsDiv.querySelector(`button[data-uri="${trackUri}"]`).previousElementSibling.querySelector('div').innerText;
const artistName = resultsDiv.querySelector(`button[data-uri="${trackUri}"]`).previousElementSibling.querySelector('span').innerText.split(' - ')[0];
currentTrackNameSpan.innerText = trackName;
currentArtistNameSpan.innerText = artistName;
togglePlayPauseButton.innerText = 'Pause';
} catch (error) {
console.error('Error playing track:', error);
}
}

// Spotify Web Playback SDK
window.onSpotifyWebPlaybackSDKReady = () => {
const token = currentAccessToken; // Use the access token from your Flask backend

const player = new Spotify.Player({
name: 'Disney Web Player',
getOAuthToken: cb => { cb(token); },
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
fetch('/transfer_playback', {
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
// Fetch user profile to display name
fetch('/user_profile?access_token=' + token)
.then(response => response.json())
.then(data => {
    displayNameSpan.innerText = data.display_name;
})
.catch(error => console.error('Error fetching profile:', error));
}