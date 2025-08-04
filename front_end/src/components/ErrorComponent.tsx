import { useEffect } from "react";
import ViewStore from "../stores/ViewStore";

const ErrorComponent = () => {
    const { errors, dismissError } = ViewStore((state: any) => state);

    useEffect(() => {
        console.log('ErrorComponent');
    }, []);

    return (
        <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-auto">
            {errors.map((error: string, idx: number) => (
                <div
                    key={idx}
                    className="bg-red-500 text-white p-5 rounded-lg shadow-2xl flex flex-col items-start min-w-[300px] max-w-xs"
                    style={{ minWidth: 300 }}
                >
                    <div className="flex w-full justify-between items-center mb-2">
                        <h1 className="text-2xl font-bold">Error</h1>
                        <button
                            className="ml-4 text-white text-lg font-bold hover:text-gray-200 focus:outline-none"
                            aria-label="Dismiss error"
                            onClick={() => dismissError(idx)}
                        >
                            ×
                        </button>
                    </div>
                    <p className="text-sm break-words">{error}</p>
                </div>
            ))}
        </div>
    );
}

export default ErrorComponent;