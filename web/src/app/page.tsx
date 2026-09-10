/**
 * `/` — the journey starts at the project list. Nothing renders here.
 */

import { redirect } from 'next/navigation';

export default function RootPage(): never {
  redirect('/projects');
}
