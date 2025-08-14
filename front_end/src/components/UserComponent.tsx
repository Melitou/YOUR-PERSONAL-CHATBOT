import UserAuthStore from "../stores/UserAuthStore";

const UserComponent = () => {
    const user = UserAuthStore((state: any) => state.user);
    
    return (
        <>
            {/* User settings section - fixed at bottom */}
            <div className="border-t border-gray-200 bg-[#f9f9f9] flex-shrink-0">
                <div className="p-3 hover:bg-[#e0e0e0] cursor-pointer transition-colors flex items-center gap-2" 
                    onClick={() => {alert("User settings and info clicked")}}
                >
                    <div className="h-6 w-6 rounded-full bg-blue-500 flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-white" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                        </svg>
                    </div>
                    {/* User name and type of user */}
                    <div className="flex flex-col">
                        <div className="text-black text-xs sm:text-sm">{user?.name}</div>
                        <div className="text-gray-500 text-xs sm:text-sm">{user?.role}</div>
                    </div>
                </div>
            </div>
        </>
    )
}   

export default UserComponent;