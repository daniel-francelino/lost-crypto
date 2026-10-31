import type { ComponentProps } from "react";
import { Button } from "lost-ui/ui/button";
import { cn } from "lost-ui/lib/cn";

export function DangerButton({
  className,
  ...props
}: Omit<ComponentProps<typeof Button>, "variant">) {
  return (
    <Button variant="destructive" className={cn("dark:bg-destructive", className)} {...props} />
  );
}
