import SidebarComponent from "../components/SidebarComponent";
import HeaderComponent from "../components/HeaderComponent";
import WelcomeScreenComponent from "../components/WelcomeScreenComponent";

const MainPage = () => {
    return (
        <div className="h-screen flex flex-row overflow-hidden w-screen">
            {/* Sidebar */}
            <div className="flex-none w-min">
                <SidebarComponent />
            </div>
            {/* Main Content */}
            <div className="flex-grow flex flex-col p-2">
                <HeaderComponent />
                <div className="flex flex-col flex-1 min-h-0 justify-center items-center">
                    <WelcomeScreenComponent />
                </div>
            </div>
            {/* Error floating component
            {errors.length > 0 && <ErrorComponent />}
            {isLoading && <LoadingComponent />} */}
        </div>
    );
}

export default MainPage; 