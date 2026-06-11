export function BrandMark({
  compact = false,
  inverse = false,
}: {
  compact?: boolean;
  inverse?: boolean;
}) {
  return (
    <span aria-label="未命名品牌" className="flex items-center gap-3">
      <span className="grid h-9 w-9 grid-cols-2 gap-1 rounded-[10px] bg-[#cbf8ff] p-1.5 shadow-sm">
        <span className="rounded-br-lg rounded-tl-md bg-[#2ecad3]" />
        <span className="rounded-bl-lg rounded-tr-md bg-[#72dde2]" />
        <span className="rounded-br-lg rounded-tl-md bg-[#b7edf0]" />
        <span className="rounded-bl-lg rounded-tr-md bg-[#42bec6]" />
      </span>
      {!compact && (
        <span
          aria-hidden="true"
          className={`brand-slot ${inverse ? "brand-slot-inverse" : ""}`}
          style={{ width: 118 }}
        />
      )}
    </span>
  );
}
