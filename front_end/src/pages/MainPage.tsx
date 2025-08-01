import SidebarComponent from "../components/SidebarComponent";
import HeaderComponent from "../components/HeaderComponent";
import ChatComponent from "../components/ChatComponent";
import WelcomeScreenComponent from "../components/WelcomeScreenComponent";
import ViewStore from "../stores/ViewStore";
import ChatbotStore from "../stores/LoadedChatbotStore";

const MainPage = () => {
    const sidebarOpen = ViewStore((state: any) => state.sidebarOpen);
    const chatbot = ChatbotStore((state: any) => state.chatbot);

    return (
        <div className="h-screen flex flex-row overflow-hidden w-screen">
            {/* Sidebar */}
            {chatbot && (
                <div className={`flex-none w-min ${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300`}>
                    <SidebarComponent />
                </div>
            )}
            {/* Main Content */}
            <div className="flex-grow flex flex-col p-2">
                <HeaderComponent />
                <div className="flex flex-col flex-1 min-h-0 justify-center items-center">
                    {chatbot ? (
                        <ChatComponent />
                    ) : (
                        <WelcomeScreenComponent />
                    )}
                </div>
            </div>
        </div>
    );
}

export default MainPage; 