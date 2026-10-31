# Calendar

`@danielsoaresf/lost-ui/calendar` has `EventCalendar`: month, week and day views, previous / today / next, a list of calendars to show or hide, and a click on an empty time to create an event. No peers. Props of each piece: [api/calendar](api/calendar.md).

```tsx
import { EventCalendar } from "@danielsoaresf/lost-ui/calendar";

<EventCalendar<Booking>
  events={bookings}
  accessors={{ id: "code", title: (b) => b.guest, start: "from", end: "to" }}
  calendars={calendars}
  onCalendarToggle={toggle}
  onEventClick={(booking) => open(booking)}
  onCreate={({ start, end, allDay }) => openForm({ start, end, allDay })}
  onRangeChange={({ start, end }) => load(start, end)}
  locale="pt-BR"
/>;
```

## Rules

- Events are **your own objects**: name their fields with `accessors` (a field name or a function). Fields called `id`, `title`, `start`, `end`, `allDay`, `calendarId`, `color`, `location` need nothing. Handlers get your object back.
- The app keeps the events. It expands recurring ones before passing them, loads with `onRangeChange` (`{ view, start, end }`, `end` is the day after the last), and decides what `onEventClick` and `onCreate` do (open a `Modal`, a `Slideover`, a form).
- Give the parent a height (`h-dvh`, `h-full`): the calendar fills it and the grid scrolls inside.
- Colours are CSS colours or tokens (`"var(--info)"`), from the event or from its calendar.
- `locale` writes dates for any `Intl` locale; without it the language of `LostI18nProvider` decides.
- Not in it yet: recurrence, a time zone per event, drag to move or resize, popovers and forms of the event, scheduling links. Do not rebuild the views in the app; ask to add what is missing to the library.
- Pieces on their own: `MonthView`, `WeekView`, `DayView`, `TimeGrid`, `CalendarDateNav`, `CalendarList`, `CalendarEventChip`, and the helpers in `calendar-model` (`monthGrid`, `startOfWeek`, `addMonths`, `layoutTimedEvents`…).
