export function applyDesignSystem(documentElement: HTMLElement) {
  documentElement.classList.add("fitician-app");
  documentElement.classList.add("fitsho-app");
  documentElement.dataset.fiticianTheme = "dark";
  documentElement.dataset.fitshoTheme = "dark";
}
