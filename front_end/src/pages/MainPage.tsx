import SidebarComponent from "../components/SidebarComponent";
import HeaderComponent from "../components/HeaderComponent";
import ChatComponent from "../components/ChatComponent";
import ThoughtVisualizerComponent from "../components/ThoughtVisualizerComponent";
import WelcomeScreenComponent from "../components/WelcomeScreenComponent";
import OrganizationsPage from "./OrganizationsPage";
import ViewStore from "../stores/ViewStore";
import LoadedChatbotStore from "../stores/LoadedChatbotStore";

const MainPage = () => {
    const { sidebarOpen, setSidebarOpen, currentView, thoughtVisualizerOpen } = ViewStore();
    const chatbot = LoadedChatbotStore((state: any) => state.loadedChatbot);

    // Show organizations page when currentView is 'organizations'
    if (currentView === 'organizations') {
        return (
            <div className="h-screen flex flex-col w-full overflow-hidden">
                {/* Header spans full width */}
                <HeaderComponent />

                {/* Organizations Page Content */}
                <div className="flex-1 min-h-0 overflow-hidden">
                    <OrganizationsPage />
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col w-full overflow-hidden">
            {/* Header spans full width */}
            <HeaderComponent />

            {/* Main layout with sidebar and content */}
            <div className="flex-1 flex flex-row min-h-0 overflow-hidden relative">
                {/* Sidebar */}
                {chatbot && (
                    <div className={`flex-none transition-all duration-300 ${sidebarOpen ? 'w-64' : 'w-0 overflow-hidden'
                        } lg:relative ${sidebarOpen ? 'absolute lg:relative inset-y-0 left-0 z-40' : ''
                        }`}>
                        <SidebarComponent />
                    </div>
                )}
                {/* Main Content */}
                <div className="flex-1 min-w-0 flex flex-row p-2">
                    {chatbot ? (
                        <>
                            {/* Chat Component - Takes remaining space in main content area */}
                            <div className={`${thoughtVisualizerOpen ? 'w-2/3' : 'w-full'} flex justify-center transition-all duration-300`}>
                                <ChatComponent />
                            </div>
                            {thoughtVisualizerOpen && (
                                <div className="flex w-1/3 h-full items-center justify-center">
                                    <ThoughtVisualizerComponent />
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="flex-1 min-w-0 flex flex-col justify-center">
                            <WelcomeScreenComponent />
                        </div>
                    )}
                </div>

                {/* Mobile overlay */}
                {sidebarOpen && (
                    <div
                        className="fixed inset-0 bg-black bg-opacity-40 z-30 lg:hidden"
                        onClick={() => setSidebarOpen(false)}
                    />
                )}
            </div>
        </div>
    );
}

export default MainPage; 