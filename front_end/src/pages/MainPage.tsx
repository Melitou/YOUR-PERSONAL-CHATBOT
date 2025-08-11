import SidebarComponent from "../components/SidebarComponent";
import HeaderComponent from "../components/HeaderComponent";
import ChatComponent from "../components/ChatComponent";
import WelcomeScreenComponent from "../components/WelcomeScreenComponent";
import ViewStore from "../stores/ViewStore";
import LoadedChatbotStore from "../stores/LoadedChatbotStore";

const MainPage = () => {
    const sidebarOpen = ViewStore((state: any) => state.sidebarOpen);
    const chatbot = LoadedChatbotStore((state: any) => state.loadedChatbot);

    return (
        <div className="h-screen flex flex-col w-full overflow-hidden">
            {/* Header spans full width */}
            <HeaderComponent />
            
            {/* Main layout with sidebar and content */}
            <div className="flex-1 flex flex-row min-h-0 overflow-hidden">
                {/* Sidebar */}
                {chatbot && (
                    <div className={`flex-none ${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300`}>
                        <SidebarComponent />
                    </div>
                )}
                {/* Main Content */}
                <div className="flex-1 min-w-0 flex flex-col p-2">
                    <div className="flex flex-row flex-1 min-h-0 min-w-0 w-full justify-center">
                        {chatbot ? (
                            <ChatComponent />
                        ) : (
                            <WelcomeScreenComponent />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default MainPage; 