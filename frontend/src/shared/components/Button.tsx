import type { MouseEventHandler, ReactNode } from "react";

type CommonProps = {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "ghost" | "dark";
};

type ButtonProps = CommonProps &
  (
    | {
        href: string;
        download?: string | boolean;
        onClick?: never;
        target?: "_blank";
      }
    | {
        href?: never;
        download?: never;
        onClick?: MouseEventHandler<HTMLButtonElement>;
        target?: never;
        type?: "button" | "submit";
      }
  );

const variants = {
  primary:
    "bg-[#cafbff] text-[#17204f] hover:bg-white focus-visible:outline-[#cafbff] shadow-[0_18px_36px_rgba(35,224,232,0.22)]",
  secondary:
    "border border-white/35 bg-white/5 text-white hover:bg-white/12 focus-visible:outline-white",
  ghost:
    "border border-slate-200 bg-white text-slate-900 hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-[#35c7ce]",
  dark:
    "bg-[#20245f] text-white hover:bg-[#171b4d] focus-visible:outline-[#35c7ce]",
} as const;

export function Button({
  children,
  className = "",
  variant = "primary",
  ...props
}: ButtonProps) {
  const classes = `inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-5 py-3 text-sm font-bold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${variants[variant]} ${className}`;

  if ("href" in props && props.href) {
    return (
      <a
        className={classes}
        download={props.download}
        href={props.href}
        rel={props.target === "_blank" ? "noreferrer" : undefined}
        target={props.target}
      >
        {children}
      </a>
    );
  }

  const type = "type" in props ? props.type : "button";

  return (
    <button className={classes} onClick={props.onClick} type={type ?? "button"}>
      {children}
    </button>
  );
}
