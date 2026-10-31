# Recipes

Forms, tables, overlays and texts. For pages and layouts see [layouts](layouts.md). Prop names are the ones in `api/<layer>.md`; check them when in doubt.

## Forms

```tsx
import {
  Form,
  FormInput,
  FormInputPassword,
  FormSelect,
  rules,
} from "@danielsoaresf/lost-ui/forms";

<Form onSubmit={() => save(values)}>
  <FormInput
    label="Email"
    type="email"
    required
    value={values.email}
    onValueChange={(email) => setValues((v) => ({ ...v, email }))}
    rules={[rules.required(), rules.email()]}
  />
  <FormInputPassword label="Password" rules={[rules.required(), rules.minLength(10)]} />
  <button type="submit">Save</button>
</Form>;
```

Many fields from data: `FormBuilder` (import by path `@danielsoaresf/lost-ui/forms/form-builder`) with `fields={[{ control: "input", name, label, rules, visible, colSpan }]}`, `columns`, `onSubmit(values)`. Masks: `<FormInput mask="(##) #####-####" unmask />`.

## DataTable

```tsx
import { DataTable, type DataTableColumn } from "@danielsoaresf/lost-ui/data";

const columns: DataTableColumn<User>[] = [
  { id: "name", header: "Name", accessor: "name", sortable: true },
  { id: "created", header: "Created", accessor: "created", cell: (row) => formatDate(row.created) },
];

<DataTable
  data={users}
  columns={columns}
  getRowId={(user) => user.id}
  total={total}
  page={page}
  pageSize={20}
  onPageChange={setPage} // server mode
  sort={sort}
  onSortChange={setSort}
  loading={isLoading}
/>;
```

Full feature table (search, selection across pages, expand, column visibility, row actions with a reason when blocked) is in the library's `docs/nuxt-components.md`.

## Toast and modal

```tsx
import { toast } from "@danielsoaresf/lost-ui/ui/sonner";
import { Modal } from "@danielsoaresf/lost-ui/elements/modal";

toast.success("Saved.");

<Modal
  open={open}
  onOpenChange={setOpen}
  title="Delete order?"
  description="This cannot be undone."
  footer={({ close }) => (
    <>
      <Button variant="outline" onClick={close}>
        Cancel
      </Button>
      <Button onClick={remove}>Delete</Button>
    </>
  )}
/>;
```

## Text in another language

```tsx
import {
  LostI18nProvider,
  registerMessages,
  useLostTranslation,
} from "@danielsoaresf/lost-ui/i18n";

registerMessages("app", { en: { hello: "Hello" }, pt: { hello: "Olá" } });
const { t } = useLostTranslation("app"); // t("hello")
```
