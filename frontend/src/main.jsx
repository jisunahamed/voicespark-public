import { StrictMode } from 'react'
// import { createRoot } from 'react-dom/client'
// import './index.css'
import App from './App.jsx'

// createRoot(document.getElementById('root')).render(
//   <StrictMode>
//     <App />
//   </StrictMode>,
// )
import { createRoot } from 'react-dom/client';
// import { BrowserRouter } from 'react-router-dom';
// import { Provider } from 'react-redux';
// import { PersistGate } from 'redux-persist/integration/react';

// // // // project imports
// import { store, persister } from './store';
// // // // import * as serviceWorker from './serviceWorker';
// import config from './config';

// style + assets
import './assets/scss/style.scss';



const root = createRoot(document.getElementById('root'));
// // 
// root.render(
//     <Provider store={store}>
//         <PersistGate loading={null} persistor={persister}>
//             <BrowserRouter basename={config.basename}>
//                 <App />
//             </BrowserRouter>
//         </PersistGate>
//     </Provider>
// );

root.render(
  <StrictMode>
    <App />
  </StrictMode>,
)


