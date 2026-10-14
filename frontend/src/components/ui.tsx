import type React from "react";
const paths: Record<string, React.ReactNode> = {
  message: (
    <>
      <path d="M21 15a3 3 0 0 1-3 3H8l-5 3V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3Z" />
      <path d="M7 8h10M7 12h7" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="3" />
      <path d="M7 3v4m10-4v4M3 10h18m-14 4h2m4 0h2m-8 4h2" />
    </>
  ),
  vote: (
    <>
      <path d="m9 3 7 4-5 9-7-4Zm-3 13H3v5h18v-5h-6" />
      <path d="M7 17h10" />
    </>
  ),
  calculator: (
    <>
      <rect x="5" y="2" width="14" height="20" rx="3" />
      <path d="M8 6h8M8 11h1m6 0h1m-8 4h1m6 0h1m-8 4h1m6 0h1" />
    </>
  ),
  "chevron-left": <path d="m14 6-6 6 6 6" />,
  wallet: (
    <>
      <path d="M20 8V6a2 2 0 0 0-2-2H6a3 3 0 0 0-3 3v11a2 2 0 0 0 2 2h15V8H6a1 1 0 0 1 0-2" />
      <path d="M20 12h-4v4h4" />
    </>
  ),
  book: (
    <>
      <path d="M5 3h14v18H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm0 14h14M7 7h8m-8 4h6" />
    </>
  ),
  chart: (
    <>
      <path d="M4 3v18h17M8 16v-4m5 4V7m5 9v-7" />
    </>
  ),
  folder: (
    <path d="M3 8V6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
  ),
  file: (
    <>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z" />
      <path d="M14 3v6h6M8 13h8m-8 4h6" />
    </>
  ),
  panel: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="3" />
      <path d="M9 4v16m7-11-3 3 3 3" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6m0-10v.1" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  chevron: <path d="m6 9 6 6 6-6" />,
  building: (
    <>
      <path d="M4 21V7l8-4 8 4v14M2 21h20M9 21v-5h6v5" />
      <path d="M8 8h1m6 0h1M8 12h1m6 0h1" />
    </>
  ),
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  people: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 5" />
    </>
  ),
  lots: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <path d="M12 3v18M3 12h18" />
    </>
  ),
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m16 16 5 5" />
    </>
  ),
  logout: (
    <>
      <path d="M9 4H4v16h5M10 12h11m-4-4 4 4-4 4" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  edit: (
    <>
      <path d="m15 4 5 5-11 11-6 1 1-6Z" />
      <path d="m13 6 5 5" />
    </>
  ),
  close: <path d="m6 6 12 12M6 18 18 6" />,
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="3" />
      <path d="m3 6 9 7 9-7" />
    </>
  ),
  shield: (
    <>
      <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z" />
      <path d="m8 12 3 3 5-6" />
    </>
  ),
};
export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.building}
    </svg>
  );
}

export function Empty({
  title,
  description,
  action,
  onAction,
}: {
  title: string;
  description: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name="building" size={28} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action && (
        <button className="button secondary" onClick={onAction}>
          <Icon name="plus" size={16} />
          {action}
        </button>
      )}
    </div>
  );
}

export function BuildingIllustration() {
  return (
    <svg
      className="building-art"
      viewBox="0 0 420 300"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="240" cy="145" r="125" fill="#315a4d" />
      <circle cx="335" cy="55" r="24" fill="#e0c889" />
      <path d="M30 263h370" stroke="#87a591" strokeWidth="2" />
      <path d="M120 263V76l90-31 90 31v187" fill="#dce5cf" />
      <path d="M210 45v218h90V76z" fill="#b5cbb4" />
      <path
        d="M105 78 210 40 315 78"
        stroke="#ecedd9"
        strokeWidth="6"
        strokeLinejoin="round"
      />
      {[0, 1, 2].map((row) =>
        [0, 1, 2].map((col) => (
          <g key={`${row}-${col}`}>
            <rect
              x={143 + col * 52}
              y={99 + row * 47}
              width="25"
              height="29"
              rx="2"
              fill={col === 1 && row === 1 ? "#f2cf7c" : "#3f6556"}
            />
            <path
              d={`M${155.5 + col * 52} ${99 + row * 47}v29`}
              stroke="#b6cbb2"
              strokeWidth="2"
            />
          </g>
        )),
      )}
      <path d="M189 263v-40a21 21 0 0 1 42 0v40" fill="#315a4d" />
      <path d="M210 215v48" stroke="#87a591" />
      <circle cx="220" cy="243" r="2" fill="#e0c889" />
      <rect x="73" y="231" width="8" height="32" fill="#9cab8d" />
      <ellipse cx="77" cy="212" rx="26" ry="38" fill="#6b9574" />
      <rect x="336" y="233" width="6" height="30" fill="#9cab8d" />
      <ellipse cx="339" cy="217" rx="22" ry="32" fill="#87a37c" />
      <path d="M103 264c8-14 18-14 25 0m167 0c8-14 18-14 25 0" fill="#87a37c" />
      <path d="M49 99h24m-12-12v24" stroke="#87a591" strokeWidth="2" />
      <circle cx="362" cy="143" r="4" fill="#b6cbb2" />
    </svg>
  );
}
