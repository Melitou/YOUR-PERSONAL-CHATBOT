import SidebarComponent from "../components/SidebarComponent";
import HeaderComponent from "../components/HeaderComponent";
import ChatComponent from "../components/ChatComponent";
import ThoughtVisualizerComponent from "../components/ThoughtVisualizerComponent";
import WelcomeScreenComponent from "../components/WelcomeScreenComponent";
import ViewStore from "../stores/ViewStore";
import LoadedChatbotStore from "../stores/LoadedChatbotStore";

const MainPage = () => {
    const sidebarOpen = ViewStore((state: any) => state.sidebarOpen);
    const chatbot = LoadedChatbotStore((state: any) => state.loadedChatbot);
    const thoughtVisualizerOpen = ViewStore((state: any) => state.thoughtVisualizerOpen);

    return (
        <div className="h-screen flex flex-col w-full overflow-hidden">
            {/* Header spans full width */}
            <HeaderComponent />
            
            {/* Main layout with sidebar and content */}
            <div className="flex-1 flex flex-row min-h-0 overflow-hidden">
                {/* Sidebar - Always visible, fixed position on the left */}
                <div className={`flex-none ${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 overflow-hidden`}>
                    <SidebarComponent />
                </div>
                
                {/* Main Content Area - Takes remaining space after sidebar */}
                <div className="flex-1 min-w-0 flex flex-row">
                    {chatbot ? (
                        <>
                            {/* Thought Visualizer - Half of main content area on the left */}
                            {/* Chat Component - Takes remaining space in main content area */}
                            <div className={`${thoughtVisualizerOpen ? 'w-2/3' : 'w-full'} flex justify-center p-2 transition-all duration-300`}>
                                <ChatComponent />
                            </div>
                            {thoughtVisualizerOpen && (
                                <div className="flex w-1/3 h-full items-center justify-center">
                                    <ThoughtVisualizerComponent />
                                </div>
                            )}
                        </>
                    ) : (
                        <>
                            {/* Welcome Screen - Takes remaining space in main content area */}
                            <div className={`${thoughtVisualizerOpen ? 'w-1/2' : 'w-full'} flex-none flex justify-center p-2 transition-all duration-300`}>
                                <WelcomeScreenComponent />
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default MainPage; 