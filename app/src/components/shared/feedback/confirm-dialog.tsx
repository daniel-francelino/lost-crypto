import { useState, type ReactNode } from "react";
import { Button } from "lost-ui/ui/button";
import { Modal } from "lost-ui/elements/modal";
import { FormInput } from "lost-ui/forms/form-input";
import { Form } from "lost-ui/forms/form";
import { rules } from "lost-ui/forms/rules";
import { DangerButton } from "@/components/shared/feedback/danger-button";
import { refusalMessage } from "@/lib/shared/api/messages";

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  onConfirm: (reason: string) => Promise<unknown>;
  destructive?: boolean;
  reasonLabel?: string;
  reasonRequired?: boolean;
  typedText?: string;
  typedLabel?: string;
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  onConfirm,
  destructive = false,
  reasonLabel,
  reasonRequired = false,
  typedText,
  typedLabel,
}: ConfirmDialogProps) {
  const [reason, setReason] = useState("");
  const [typed, setTyped] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = (next: boolean) => {
    if (pending) return;
    if (!next) {
      setReason("");
      setTyped("");
      setError(null);
    }
    onOpenChange(next);
  };

  const submit = async () => {
    setPending(true);
    setError(null);
    try {
      await onConfirm(reason.trim());
      setReason("");
      setTyped("");
      onOpenChange(false);
    } catch (failure) {
      setError(refusalMessage(failure));
    } finally {
      setPending(false);
    }
  };

  return (
    <Modal
      open={open}
      onOpenChange={close}
      title={title}
      description={description}
      dismissible={!pending}
    >
      <Form onSubmit={() => void submit()} className="space-y-4">
        {reasonLabel === undefined ? null : (
          <FormInput
            label={reasonLabel}
            value={reason}
            onValueChange={setReason}
            maxLength={200}
            rules={reasonRequired ? [rules.required("Informe o motivo.")] : []}
          />
        )}
        {typedText === undefined ? null : (
          <FormInput
            label={typedLabel ?? `Digite "${typedText}" para confirmar`}
            value={typed}
            onValueChange={setTyped}
            autoComplete="off"
            rules={[rules.matches(() => typedText, "O texto digitado não confere.")]}
          />
        )}
        {error === null ? null : (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" disabled={pending} onClick={() => close(false)}>
            Cancelar
          </Button>
          {destructive ? (
            <DangerButton type="submit" disabled={pending}>
              {pending ? "Aguarde…" : confirmLabel}
            </DangerButton>
          ) : (
            <Button type="submit" disabled={pending}>
              {pending ? "Aguarde…" : confirmLabel}
            </Button>
          )}
        </div>
      </Form>
    </Modal>
  );
}
