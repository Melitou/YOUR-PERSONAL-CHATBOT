declare module 'zustand' {
    export function create<T>(fn: any): T;
}

declare module 'react' {
    export * from '@types/react';
}

declare module 'react-dom' {
    export * from '@types/react-dom';
}

declare module 'react/jsx-runtime' {
    export const jsx: any;
    export const jsxs: any;
    export const Fragment: any;
}
