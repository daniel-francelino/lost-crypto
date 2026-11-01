import { Inbox } from "lucide-react";
import { Empty as LostEmpty, type EmptyProps } from "lost-ui/data/empty";

export function EmptyState({ icon, ...props }: EmptyProps) {
  return <LostEmpty {...props} icon={icon ?? <Inbox aria-hidden="true" />} />;
}
