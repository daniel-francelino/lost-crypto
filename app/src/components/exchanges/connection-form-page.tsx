import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { Form } from "lost-ui/forms/form";
import { FormCheckbox } from "lost-ui/forms/form-checkbox";
import { FormInput } from "lost-ui/forms/form-input";
import { FormInputPassword } from "lost-ui/forms/form-input-password";
import { FormSelect } from "lost-ui/forms/form-select";
import { rules } from "lost-ui/forms/rules";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { useCapabilities } from "@/hooks/shared/use-system";
import { createConnection } from "@/lib/exchanges/exchanges.api";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Environment } from "@/lib/shared/enums";
import { AppRoute } from "@/lib/shared/routes";

const MIN_KEY = 8;

export function ConnectionFormPage() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const capabilities = useCapabilities();
  const [exchange, setExchange] = useState("binance");
  const [environment, setEnvironment] = useState<string>(Environment.Testnet);
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isLive = environment === Environment.Live;
  const liveBlocked = capabilities.data?.live_available === false;
  const exchanges = capabilities.data?.exchanges ?? ["binance"];

  const mutation = useMutation({
    mutationFn: () =>
      createConnection({
        exchange,
        environment,
        confirm_real_money: isLive && confirmed,
        label: label.trim(),
        api_key: apiKey.trim(),
        api_secret: apiSecret.trim(),
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: QueryKey.Exchanges.connections() });
      toast.success("Conexão criada.");
      await navigate({ to: AppRoute.Exchanges });
    },
    onError: (failure) => setError(errorMessage(failure)),
    onSettled: () => {
      setApiKey("");
      setApiSecret("");
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Nova conexão"
        description="A chave é criptografada no servidor e nunca volta para esta tela."
      />
      <Card>
        <CardContent className="pt-6">
          <Form
            onSubmit={() => {
              setError(null);
              mutation.mutate();
            }}
            className="max-w-xl space-y-4"
          >
            <FormSelect
              label="Exchange"
              items={exchanges.map((value) => ({ label: value, value }))}
              value={exchange}
              onValueChange={setExchange}
            />
            <FormSelect
              label="Ambiente"
              items={[
                { label: "TESTNET (dinheiro fictício)", value: Environment.Testnet },
                {
                  label: "LIVE (dinheiro real)",
                  value: Environment.Live,
                  disabled: liveBlocked,
                },
              ]}
              value={environment}
              onValueChange={setEnvironment}
            />
            {liveBlocked ? (
              <p className="text-sm text-muted-foreground">
                O live está indisponível neste ambiente:{" "}
                {capabilities.data?.live_blockers.join("; ")}.
              </p>
            ) : null}
            <FormInput
              label="Nome"
              required
              value={label}
              onValueChange={setLabel}
              rules={[rules.required("Informe um nome para reconhecer esta chave.")]}
            />
            <FormInputPassword
              label="Chave de API"
              required
              autoComplete="off"
              name="exchange-key"
              value={apiKey}
              onValueChange={setApiKey}
              rules={[
                rules.required("Informe a chave."),
                rules.minLength(MIN_KEY, "Chave muito curta."),
              ]}
            />
            <FormInputPassword
              label="Segredo da API"
              required
              autoComplete="off"
              name="exchange-secret"
              value={apiSecret}
              onValueChange={setApiSecret}
              rules={[
                rules.required("Informe o segredo."),
                rules.minLength(MIN_KEY, "Segredo muito curto."),
              ]}
            />
            {isLive ? (
              <>
                <Alert className="border-live/60">
                  <AlertTitle>Dinheiro real</AlertTitle>
                  <AlertDescription>
                    Use uma chave somente de trade, sem permissão de saque ou transferência e
                    restrita ao IP do servidor. O worker recusa chaves mais permissivas.
                  </AlertDescription>
                </Alert>
                <FormCheckbox
                  label="Entendo que esta conexão usa dinheiro real."
                  value={confirmed}
                  onValueChange={setConfirmed}
                  rules={[(value) => (value === true ? undefined : "Confirme para continuar.")]}
                />
              </>
            ) : null}
            {error === null ? null : (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <div className="flex gap-2">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Salvando…" : "Criar conexão"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => void navigate({ to: AppRoute.Exchanges })}
              >
                Cancelar
              </Button>
            </div>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
