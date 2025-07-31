import { useState } from "react";
import { FaBars, FaTimes } from "react-icons/fa";
import UserComponent from "./UserComponent";

const SidebarComponent = () => {

    {/* Sidebar Component */}

    const [sidebarOpen, setSidebarOpen] = useState(false);

    // Fake conversations
    const chatbots = [
        {
            chatbot_id: 1,
            chatbot_title: "ChatBot 1"
        },
        {
            chatbot_id: 2,
            chatbot_title: "ChatBot 2"
        },
        {
            chatbot_id: 3,
            chatbot_title: "ChatBot 3"
        },
        {
            chatbot_id: 4,
            chatbot_title: "ChatBot 4"
        },
        {
            chatbot_id: 5,
            chatbot_title: "ChatBot 5"
        },
        {
            chatbot_id: 6,
            chatbot_title: "ChatBot 6"
        },
        {
            chatbot_id: 7,
            chatbot_title: "ChatBot 7"
        },
        {
            chatbot_id: 8,
            chatbot_title: "ChatBot 8"
        },
        {
            chatbot_id: 9,
            chatbot_title: "ChatBot 9"
        },
        {
            chatbot_id: 10,
            chatbot_title: "ChatBot 10"
        },
        {
            chatbot_id: 11,
            chatbot_title: "ChatBot 11"
        },
        {
            chatbot_id: 12,
            chatbot_title: "ChatBot 12"
        },
        {
            chatbot_id: 13,
            chatbot_title: "ChatBot 13"
        },
        {
            chatbot_id: 14,
            chatbot_title: "ChatBot 14"
        },
        {
            chatbot_id: 15,
            chatbot_title: "ChatBot 15"
        },
        {
            chatbot_id: 16,
            chatbot_title: "ChatBot 16"
        },
        {
            chatbot_id: 17,
            chatbot_title: "ChatBot 17"
        },
        {
            chatbot_id: 18,
            chatbot_title: "ChatBot 18"
        },
        {
            chatbot_id: 19,
            chatbot_title: "ChatBot 19"
        },
        {
            chatbot_id: 20,
            chatbot_title: "ChatBot 20"
        },
        {
            chatbot_id: 21,
            chatbot_title: "ChatBot 21"
        },
        {
            chatbot_id: 22,
            chatbot_title: "ChatBot 22"
        },
        {
            chatbot_id: 23,
            chatbot_title: "ChatBot 23"
        },
        {
            chatbot_id: 24,
            chatbot_title: "ChatBot 24"
        },
        {
            chatbot_id: 25,
            chatbot_title: "ChatBot 25"
        },
        {
            chatbot_id: 26,
            chatbot_title: "ChatBot 26"
        },
        {
            chatbot_id: 27,
            chatbot_title: "ChatBot 27"
        },
        {
            chatbot_id: 28,
            chatbot_title: "ChatBot 28"
        },
        {
            chatbot_id: 29,
            chatbot_title: "ChatBot 29"
        },
        {
            chatbot_id: 30,
            chatbot_title: "ChatBot 30"
        },
        {
            chatbot_id: 31,
            chatbot_title: "ChatBot 31"
        },
        {
            chatbot_id: 32,
            chatbot_title: "ChatBot 32"
        },
        {
            chatbot_id: 33,
            chatbot_title: "ChatBot 33"
        },
        {
            chatbot_id: 34,
            chatbot_title: "ChatBot 34"
        },
        {
            chatbot_id: 35,
            chatbot_title: "ChatBot 35"
        },
        {
            chatbot_id: 36,
            chatbot_title: "ChatBot 36"
        },
        {
            chatbot_id: 37,
            chatbot_title: "ChatBot 37"
        },
        {
            chatbot_id: 38,
            chatbot_title: "ChatBot 38"
        },
        {
            chatbot_id: 39,
            chatbot_title: "ChatBot 39"
        },
        {
            chatbot_id: 40,
            chatbot_title: "ChatBot 40"
        },
        {
            chatbot_id: 41,
            chatbot_title: "ChatBot 41"
        }, 
    ]

    return (
        <>
            {/* Hamburger button for mobile */}
            <button
                className="fixed top-4 left-4 z-50 sm:hidden bg-gray-800 text-white p-2 rounded-md shadow-lg"
                onClick={() => setSidebarOpen(true)}
                aria-label="Open sidebar"
            >
                <FaBars size={24} />
            </button>

            <aside
                className={`
                    fixed top-0 left-0 h-screen w-64 bg-[#f9f9f9] z-40 transform
                    ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
                    transition-transform duration-300
                    sm:translate-x-0 sm:static sm:h-screen
                    flex flex-col
                `}
                style={{ boxSizing: "border-box" }}
            >
                {/* Close button for mobile */}
                <button
                    className="absolute top-4 right-4 sm:hidden text-black z-50"
                    onClick={() => setSidebarOpen(false)}
                    aria-label="Close sidebar"
                >
                    <FaTimes size={24} />
                </button>

                {/* Chatbots action buttons */}
                <div className="flex-shrink-0 p-3 pt-16 sm:pt-3 border-b border-gray-200 flex flex-col gap-2">
                    <button className="p-3 w-full rounded-md hover:bg-[#efefef] transition-colors flex items-center justify-start gap-2 text-black text-xs sm:text-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                        </svg>
                        New Chatbot
                    </button>
                    <button className="p-3 w-full rounded-md hover:bg-[#efefef] transition-colors flex items-center justify-start gap-2 text-black text-xs sm:text-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                        </svg>
                        Manage Chatbots
                    </button>
                </div>

                {/* Scrollable chatbot list */}
                <div className="flex-1 min-h-0 overflow-y-auto pt-3 px-3 pb-3">
                    <div className="flex flex-col gap-2">
                        {chatbots.map((item) => (
                            <div key={item.chatbot_id} className="p-2 rounded-md hover:bg-[#efefef] cursor-pointer transition-colors flex items-center text-black" onClick={() => {
                                setSidebarOpen(false); // Close sidebar on mobile after selecting
                            }}>
                                <div className="truncate text-black text-xs sm:text-sm">{item.chatbot_title}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* User settings section - fixed at bottom */}
                <UserComponent />
            </aside>

            {/* Overlay for mobile when sidebar is open */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-40 z-30 sm:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}
        </> 
    );
}

export default SidebarComponent;