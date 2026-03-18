# TypeScript / React

First-class TypeScript support via the NPM package. Works in React, Next.js, Vite, and modern frameworks.

### Installation

```bash
npm install storage1024
```

### TypeScript Setup

```typescript
import s1024 from 'storage1024';

s1024.set_userID('YOUR_PROJECT_ID');
s1024.set_token('YOUR_TOKEN');

const score: string = await s1024.get_gv('score');
console.log(score);
```

### React Hook Example

```tsx
import { useEffect, useState } from 'react';
import s1024 from 'storage1024';

export function useStorageVar(key: string) {
  const [value, setValue] = useState<string | null>(null);

  useEffect(() => {
    // Ideally set these in a central config or env variables
    s1024.set_userID(process.env.NEXT_PUBLIC_S1024_ID!);
    s1024.set_token(process.env.NEXT_PUBLIC_S1024_TOKEN!);
    
    s1024.get_gv(key).then(setValue);
  }, [key]);

  return value;
}

// Usage in component:
// const score = useStorageVar('score');
```
