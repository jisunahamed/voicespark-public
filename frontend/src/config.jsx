let BACKEND_SERVER = null;
let SCRAPER_SERVER = null;
if (import.meta.env.VITE_BACKEND_SERVER) {
    BACKEND_SERVER = import.meta.env.VITE_BACKEND_SERVER;
} else {
    BACKEND_SERVER = "http://localhost:8000/";
}
if (import.meta.env.VITE_SCRAPER_BACKEND_SERVER) {
    SCRAPER_SERVER = import.meta.env.VITE_SCRAPER_BACKEND_SERVER;
} else {
    SCRAPER_SERVER = "http://localhost:8000/";
}

const config = {
    basename: '/Blaze',
    defaultPath: '/Blaze',
    fontFamily: `'Roboto', sans-serif`,
    borderRadius: 12,
    API_SERVER: BACKEND_SERVER,
    SCRAPER_SERVER: SCRAPER_SERVER,
};

export default config;
