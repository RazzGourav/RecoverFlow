export default function GlobalLoading() {
  return (
    <div className="min-h-screen bg-[#0b1326] flex flex-col items-center justify-center text-white/50">
      <div className="relative flex h-16 w-16 mb-4">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#06b6d4] opacity-20"></span>
        <span className="relative inline-flex rounded-full h-16 w-16 bg-[#06b6d4]/10 border-2 border-[#06b6d4] shadow-[0_0_15px_rgba(6,182,212,0.5)]">
          <svg className="animate-spin m-auto h-8 w-8 text-[#06b6d4]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </span>
      </div>
      <p className="font-mono text-sm tracking-widest uppercase text-[#06b6d4] animate-pulse">Initializing Interface...</p>
    </div>
  );
}
