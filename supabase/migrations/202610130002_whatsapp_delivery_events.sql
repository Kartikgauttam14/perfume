begin;
create table public.whatsapp_delivery_events (
  event_key text primary key,
  outgoing_id text not null,
  delivery_state text not null,
  event_at timestamptz not null,
  received_at timestamptz not null default now(),
  error_code integer
);
create index whatsapp_delivery_outgoing_id on public.whatsapp_delivery_events(outgoing_id);
alter table public.whatsapp_delivery_events enable row level security;
revoke all on public.whatsapp_delivery_events from public, anon, authenticated;
grant select, insert, update, delete on public.whatsapp_delivery_events to service_role;
commit;
