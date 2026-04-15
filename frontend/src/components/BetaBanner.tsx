export function BetaBanner() {
  return (
    <div className="w-full border-b border-green-500/30 bg-green-500/10 px-6 py-2.5">
      <p className="text-center text-x text-green-700 dark:text-green-400 leading-relaxed">
        <span className="font-semibold">BETA</span> — Dit dashboard is in ontwikkeling —
        <br />
        Gegevens zijn afkomstig van open overheidsdata (Tweede Kamer, Officiële Bekendmakingen), CBS en Wetgeving opzoeken functioneren nog niet.
        De volledigheid, filtering, sortering en zoekfunctionaliteit zijn ook nog niet gegarandeerd.
        <br />
        Dit is dus niet geschikt voor gebruik!
      </p>
    </div>
  );
}
