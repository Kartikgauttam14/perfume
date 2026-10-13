begin;
create table public.whatsapp_reply_events (
  message_id text primary key,
  recipient text not null,
  incoming_at timestamptz not null,
  received_at timestamptz not null default now(),
  state text not null check (state in ('disabled','claimed','accepted','failed','uncertain')),
  outgoing_id text
);
alter table public.whatsapp_reply_events enable row level security;
revoke all on public.whatsapp_reply_events from public, anon, authenticated;
grant select, insert, update, delete on public.whatsapp_reply_events to service_role;
commit;
