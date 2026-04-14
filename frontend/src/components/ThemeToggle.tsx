interface Props {
  light: boolean;
  onToggle: () => void;
}

export function ThemeToggle({ light, onToggle }: Props) {
  return (
    <button
      onClick={onToggle}
      title={light ? "Schakel naar donker thema" : "Schakel naar licht thema"}
      className="flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-800/40
                 px-3 py-1.5 text-xs text-slate-400 transition-all duration-150
                 hover:border-ink-600 hover:text-slate-200"
    >
      {light ? (
        /* Moon icon */
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75
               0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21
               12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
        </svg>
      ) : (
        /* Sun icon */
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12
               18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75
               12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
        </svg>
      )}
      {light ? "Donker" : "Licht"}
    </button>
  );
}
