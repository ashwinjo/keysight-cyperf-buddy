import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md font-medium tracking-luxury uppercase transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-luxury-accent focus-visible:ring-offset-2 focus-visible:ring-offset-luxury-bg disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-luxury-accent text-luxury-bg hover:bg-luxury-accent-alt active:scale-95 shadow-elegant",
        destructive: "bg-red-900 text-luxury-text hover:bg-red-800 active:scale-95 shadow-elegant",
        outline:
          "border border-luxury-border bg-transparent text-luxury-text hover:border-luxury-accent hover:text-luxury-accent transition-colors",
        secondary: "bg-luxury-bg-subtle text-luxury-text hover:bg-luxury-border border border-luxury-border",
        ghost: "text-luxury-text-secondary hover:text-luxury-text hover:bg-luxury-bg-subtle",
        link: "text-luxury-accent underline-offset-4 hover:text-luxury-accent-alt hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2 text-sm",
        sm: "h-9 px-3 text-xs",
        lg: "h-12 px-8 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
