export const THEME_STORAGE_KEY = "itspeak-color-theme";
export const LIGHT_THEME = "light";
export const DARK_THEME = "dark";

export function normalizeTheme(value) {
  return value === DARK_THEME ? DARK_THEME : LIGHT_THEME;
}

export function createThemeInitializerScript() {
  return `(function(){try{var value=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});document.documentElement.dataset.theme=value===${JSON.stringify(DARK_THEME)}?${JSON.stringify(DARK_THEME)}:${JSON.stringify(LIGHT_THEME)};}catch(error){document.documentElement.dataset.theme=${JSON.stringify(LIGHT_THEME)};}})();`;
}
