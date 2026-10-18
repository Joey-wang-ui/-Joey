-- Run once in YOUR Supabase project's SQL Editor. This creates only Joey objects.
-- No existing local todos are uploaded by this script.
begin;

create table if not exists public.joey_todos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null check (char_length(btrim(title)) between 1 and 200),
  due_date date,
  completed boolean not null default false,
  created_at timestamptz not null default now(),
  import_key text,
  unique (user_id, import_key)
);

create index if not exists joey_todos_user_id_idx on public.joey_todos(user_id);
alter table public.joey_todos enable row level security;

-- Revoke anonymous access even if the project's default grants are permissive.
revoke all on table public.joey_todos from public, anon;
grant select, insert, update, delete on table public.joey_todos to authenticated;

drop policy if exists joey_select_own on public.joey_todos;
create policy joey_select_own on public.joey_todos for select to authenticated
  using ((select auth.uid()) = user_id);
drop policy if exists joey_insert_own on public.joey_todos;
create policy joey_insert_own on public.joey_todos for insert to authenticated
  with check ((select auth.uid()) = user_id);
drop policy if exists joey_update_own on public.joey_todos;
create policy joey_update_own on public.joey_todos for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists joey_delete_own on public.joey_todos;
create policy joey_delete_own on public.joey_todos for delete to authenticated
  using ((select auth.uid()) = user_id);

commit;
