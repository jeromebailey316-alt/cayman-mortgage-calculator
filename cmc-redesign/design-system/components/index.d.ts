import type * as React from 'react';

/** Lucide subset bundled with the system: house, calculator, percent, landmark, file-text, receipt, map-pin, bed-double, bath, ruler, search, heart, arrow-right, chevron-down, mail, phone, shield-check, trending-up, menu, info. */
export type IconName = 'house' | 'calculator' | 'percent' | 'landmark' | 'file-text' | 'receipt' | 'map-pin' | 'bed-double' | 'bath' | 'ruler' | 'search' | 'heart' | 'arrow-right' | 'chevron-down' | 'mail' | 'phone' | 'shield-check' | 'trending-up' | 'menu' | 'info';
export interface IconProps { name: IconName; size?: number; strokeWidth?: number; className?: string }
export declare function Icon(props: IconProps): React.ReactElement;

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** primary = navy-700 fill; secondary = white with line-300 border; ghost = text only; onDark = white fill for navy surfaces */
  variant?: 'primary' | 'secondary' | 'ghost' | 'onDark';
  size?: 'md' | 'sm';
  /** Renders an <a> instead of a <button> */
  href?: string;
  iconLeft?: IconName; iconRight?: IconName;
  block?: boolean;
}
export declare function Button(props: ButtonProps): React.ReactElement;

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string; hint?: string; error?: string;
  /** Text shown inside the control before the value, e.g. "CI$" */
  prefix?: string;
  /** Text shown inside the control after the value, e.g. "%" */
  suffix?: string;
  /** Two-way binding to one of the site's shared inputs (CMC.inputs) */
  bind?: SharedInputKey;
}
export declare function Input(props: InputProps): React.ReactElement;

export type SharedInputKey = 'price' | 'deposit' | 'rate' | 'term';
export interface SharedInputs {
  price: number; deposit: number; rate: number; term: number;
  /** Display currency; all stored money is CI$ */
  currency: 'KYD' | 'USD';
  /** Multiplier from CI$ to the display currency (1 or 1.20) and its symbol — read-only, derived */
  fx: number; symbol: 'CI$' | 'US$';
}
/** Purchase price, deposit %, rate and term — entered once, used on every page. Persisted in localStorage ("cmc.inputs"). */
export declare const inputs: {
  key: string; defaults: Pick<SharedInputs, SharedInputKey | 'currency'>; usdPerKyd: number;
  get(fallback?: Partial<SharedInputs>): SharedInputs;
  set(partial: Partial<SharedInputs>): void;
  reset(): void;
  subscribe(fn: (values: SharedInputs) => void): () => void;
};
/** React hook: [values, set] bound to CMC.inputs */
export declare function useInputs(fallback?: Partial<SharedInputs>): [SharedInputs, (partial: Partial<SharedInputs>) => void];

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string; hint?: string; error?: string;
  options: Array<string | { value: string | number; label: string }>;
}
export declare function Select(props: SelectProps): React.ReactElement;

export interface PillTabsProps {
  items: Array<string | { value: string; label: string }>;
  value: string;
  onChange?: (value: string) => void;
  className?: string;
}
export declare function PillTabs(props: PillTabsProps): React.ReactElement;

export interface BadgeProps {
  /** navy = for sale; teal = for rent / new / positive; neutral = informational; tint = teal text on teal-100 */
  tone?: 'navy' | 'teal' | 'neutral' | 'tint';
  className?: string; children?: React.ReactNode;
}
export declare function Badge(props: BadgeProps): React.ReactElement;

export interface ListingCardProps {
  price: number; currency?: string;
  /** "mo" renders "/mo" after a rental price */
  period?: string;
  address: string; locality?: string;
  beds?: number; baths?: number; sqft?: number;
  image?: string; imageAlt?: string;
  badge?: string; badgeTone?: BadgeProps['tone'];
  /** Estimated monthly payment shown as a teal line under the address */
  monthly?: number;
  agency?: string;
  /** The listing on the agent's own site; absolute http(s) links open in a new tab with a "View on agent's site" cue */
  href?: string;
  favourited?: boolean; onFavourite?: () => void;
  /** "Compare" chip on the photo; the page keeps the selection */
  compared?: boolean; onCompare?: () => void;
  className?: string;
}
export declare function ListingCard(props: ListingCardProps): React.ReactElement;

export interface CalculatorPanelProps {
  /** Used only until the visitor has entered values; the panel reads and writes CMC.inputs */
  defaults?: Partial<SharedInputs>;
  currency?: string;
  tab?: 'buy' | 'refi' | 'afford';
  hideTabs?: boolean;
  /** Two-column layout for sidebars and phones */
  compact?: boolean;
  /** Tabs that navigate to another page instead of switching in place */
  tabLinks?: Partial<Record<'buy' | 'refi' | 'afford', string>>;
  ctaLabel?: string; href?: string; onSubmit?: () => void;
  /** One line under the panel, e.g. the rate source */
  note?: string;
  className?: string;
}
export declare function CalculatorPanel(props: CalculatorPanelProps): React.ReactElement;
/** Monthly payment for a principal at an annual % rate over N years (standard amortising formula). */
export declare function payment(principal: number, annualRate: number, years: number): number;

export interface HeaderProps {
  /** URL of cmc-secondary-color.svg */
  logo?: string;
  /** URL of cmc-secondary-reversed.svg, used when dark */
  logoReversed?: string;
  dark?: boolean;
  homeHref?: string;
  /** Logo height in px inside the fixed 72px row; 40 default, 64 max */
  logoHeight?: number;
  /** An item with `menu` opens a dropdown on hover/focus; `open: true` keeps it open (for mockups) */
  nav?: Array<{ label: string; href?: string; active?: boolean; open?: boolean; menu?: Array<{ label: string; href?: string; icon?: IconName; description?: string; active?: boolean }> }>;
  cta?: { label: string; href?: string; icon?: IconName };
  utility?: { items?: Array<{ icon?: IconName; text: string }>; right?: React.ReactNode };
  className?: string;
}
export declare function Header(props: HeaderProps): React.ReactElement;

export interface FooterProps {
  /** URL of cmc-secondary-reversed.svg */
  logoReversed?: string;
  blurb?: string;
  columns?: Array<{ title: string; links: Array<{ label: string; href?: string }> }>;
  legal?: string;
  legalLinks?: Array<{ label: string; href?: string }>;
  className?: string;
}
export declare function Footer(props: FooterProps): React.ReactElement;

export interface BackToTopProps { /** Scroll distance in px before the button appears (default 400) */ after?: number; className?: string }
/** Floating button that scrolls back to the top; place above the Footer on every page */
export declare function BackToTop(props: BackToTopProps): React.ReactElement;

export interface BylineProps { author?: string; reviewer?: string; checked?: string; updated?: string; note?: string; className?: string }
/** Provenance strip: written by, reviewed by, sources checked, last updated */
export declare function Byline(props: BylineProps): React.ReactElement;

declare global {
  interface Window {
    CMC: {
      Icon: typeof Icon; Button: typeof Button; Input: typeof Input; Select: typeof Select; PillTabs: typeof PillTabs;
      Badge: typeof Badge; ListingCard: typeof ListingCard; CalculatorPanel: typeof CalculatorPanel; Header: typeof Header; Footer: typeof Footer; Byline: typeof Byline; BackToTop: typeof BackToTop; payment: typeof payment;
      inputs: typeof inputs; useInputs: typeof useInputs;
    };
  }
}
