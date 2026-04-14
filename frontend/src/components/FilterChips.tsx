const TYPE_COLORS: Record<string, string> = {
  Motie:                          "bg-violet-900/50 text-violet-300 border-violet-700/60 hover:border-violet-500",
  Amendement:                     "bg-blue-900/50 text-blue-300 border-blue-700/60 hover:border-blue-500",
  Brief:                          "bg-teal-900/50 text-teal-300 border-teal-700/60 hover:border-teal-500",
  Kamervraag:                     "bg-orange-900/50 text-orange-300 border-orange-700/60 hover:border-orange-500",
  Verslag:                        "bg-slate-700/50 text-slate-300 border-slate-600/60 hover:border-slate-400",
  Rapport:                        "bg-green-900/50 text-green-300 border-green-700/60 hover:border-green-500",
  Vergaderverslag:                "bg-pink-900/50 text-pink-300 border-pink-700/60 hover:border-pink-500",
  Antwoord:                       "bg-amber-900/50 text-amber-300 border-amber-700/60 hover:border-amber-500",
  Besluitenlijst:                 "bg-cyan-900/50 text-cyan-300 border-cyan-700/60 hover:border-cyan-500",
};

const ACTIVE_COLORS: Record<string, string> = {
  Motie:          "bg-violet-600 text-white border-violet-500",
  Amendement:     "bg-blue-600 text-white border-blue-500",
  Brief:          "bg-teal-600 text-white border-teal-500",
  Kamervraag:     "bg-orange-500 text-white border-orange-400",
  Verslag:        "bg-slate-500 text-white border-slate-400",
  Rapport:        "bg-green-600 text-white border-green-500",
  Vergaderverslag:"bg-pink-600 text-white border-pink-500",
  Antwoord:       "bg-amber-500 text-white border-amber-400",
  Besluitenlijst: "bg-cyan-600 text-white border-cyan-500",
};

interface Props {
  available: string[];
  selected: string[];
  onChange: (types: string[]) => void;
}

export function FilterChips({ available, selected, onChange }: Props) {
  const toggle = (type: string) => {
    onChange(
      selected.includes(type)
        ? selected.filter((t) => t !== type)
        : [...selected, type]
    );
  };

  return (
    <div className="flex flex-wrap gap-1.5">
      {available.map((type) => {
        const active = selected.includes(type);
        const base = "badge border cursor-pointer transition-all duration-150 select-none";
        const colors = active
          ? ACTIVE_COLORS[type] ?? "bg-amber-500 text-ink-900 border-amber-400"
          : TYPE_COLORS[type] ?? "bg-ink-800 text-slate-400 border-ink-600 hover:border-slate-400";
        return (
          <button key={type} className={`${base} ${colors}`} onClick={() => toggle(type)}>
            {type}
          </button>
        );
      })}
      {selected.length > 0 && (
        <button
          className="badge border border-ink-600 bg-transparent text-slate-500 hover:text-slate-300 cursor-pointer transition-colors"
          onClick={() => onChange([])}
        >
          Wis filters
        </button>
      )}
    </div>
  );
}