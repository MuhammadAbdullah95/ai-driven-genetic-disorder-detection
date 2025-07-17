// This is a server component to ensure instant redirect with no UI flash
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/chat');
}