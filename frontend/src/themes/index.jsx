
import {createTheme} from '@mui/material';

// assets
import colors from '../assets/scss/_themes-vars.module.scss';

// project imports
import { componentStyleOverrides } from './compStyleOverride';
import { themePalette } from './palette';
import { themeTypography } from './typography';
/**
 * Represent theme style and structure as per Material-UI
 * @param {JsonObject} customization customization parameter object
 */

export function theme(customization) {
    const color = colors;

    let themeOption = {
        colors: color,
        heading: color.grey900,
        paper: color.paper,
        backgroundDefault: color.paper,
        background: color.primaryLight,
        darkTextPrimary: color.grey700,
        darkTextSecondary: color.grey500,
        textDark: color.grey900,
        menuSelected: color.secondaryDark,
        menuSelectedBack: color.secondaryLight,
        divider: color.grey200,
        customization: customization
    };

    return createTheme({
        direction: 'ltr',
        palette: themePalette(themeOption),
        mixins: {
            toolbar: {
                minHeight: '48px',
                padding: '16px',
                '@media (min-width: 600px)': {
                    minHeight: '48px'
                }
            }
        },
        breakpoints: {
            values: {
                xs: 0,
                sm: 600,
                md: 960,
                lg: 1280,
                xl: 1920
            }
        },
        typography: themeTypography(themeOption),
        components: componentStyleOverrides(themeOption)
    });
}


// const theme = createTheme({
//   palette: {
//     primary: { main: '#7c3aed' },
//     secondary: { main: '#a78bfa' },
//     background: { default: '#f8f7fc', paper: '#ffffff' },
//   },
//   typography: {
//     fontFamily: "'DM Sans', sans-serif",
//     h5: { fontWeight: 700 },
//     h6: { fontWeight: 600 },
//   },
//   components: {
//     MuiListItemButton: {
//       styleOverrides: {
//         root: {
//           borderRadius: 8,
//           margin: '2px 8px',
//           '&.Mui-selected': {
//             backgroundColor: '#ede9fe',
//             color: '#7c3aed',
//             '& .MuiListItemIcon-root': { color: '#7c3aed' },
//           },
//           '&:hover': { backgroundColor: '#f3f0ff' },
//         },
//       },
//     },
//     MuiCard: {
//       styleOverrides: {
//         root: { borderRadius: 14, boxShadow: '0 1px 4px rgba(0,0,0,0.07)' },
//       },
//     },
//   },
// });

export default theme;