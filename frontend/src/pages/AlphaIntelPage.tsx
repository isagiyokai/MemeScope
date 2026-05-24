import TopBar from "@/components/TopBar";
import AlphaIntelView from "@/pages/AlphaIntelView";

const AlphaIntelPage = () => {
  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <TopBar />
      <div className="flex-1 overflow-y-auto">
        <AlphaIntelView />
      </div>
    </div>
  );
};

export default AlphaIntelPage;
