export function BrandMark() {
  return (
    <span className="brand-mark copro-brand-mark">
      <img
        src={`${import.meta.env.BASE_URL}copro-mark.svg`}
        width="42"
        height="42"
        alt=""
        aria-hidden="true"
        draggable={false}
      />
    </span>
  );
}
