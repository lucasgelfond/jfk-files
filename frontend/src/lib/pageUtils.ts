import { supabase } from '../utils/supabase';

export type PageData = {
	page_number: number;
	cloudinary: {
		secure_url: string;
		public_id: string;
		width: number;
		height: number;
		format: string;
		bytes: number;
	};
	ocr_result: string;
};

export type PageMap = Record<number, PageData>;

export async function fetchAllPages(parentRecordId: string): Promise<PageMap> {
	const { data } = await supabase
		.from('page')
		.select('page_number,cloudinary,ocr_result')
		.eq('parent_record_id', parentRecordId);

	if (!data) return {};

	return data.reduce((acc, page) => {
		// Convert page_number to number since it's stored as string
		const pageNum = parseInt(page.page_number as string, 10);
		if (!isNaN(pageNum)) {
			acc[pageNum] = {
				...page,
				page_number: pageNum
			};
		}
		return acc;
	}, {} as PageMap);
}
